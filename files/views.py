import io
import os
import tempfile

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.http import FileResponse, HttpResponseBadRequest
from django.urls import reverse
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from .models import DriveAppCredentials
from .utils import get_flow, get_drive_service


def home(request):
    if request.user.is_authenticated:
        return redirect("/files/")
    return redirect("/login/")


@user_passes_test(lambda u: u.is_superuser)
@login_required
def google_login(request):
    """
    Admin-only Google OAuth connect flow.

    After the callback, we store credentials globally for the app so that
    other logged-in Django users can upload/search/download without repeating
    the Google OAuth flow.
    """
    redirect_uri = request.build_absolute_uri(reverse("oauth2callback"))
    flow = get_flow(redirect_uri=redirect_uri)

    auth_url, state = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true",
    )

    request.session["state"] = state
    # With PKCE enabled in google-auth-oauthlib, Google requires the matching
    # code_verifier during the token exchange on the callback.
    request.session["code_verifier"] = getattr(flow, "code_verifier", None)

    return redirect(auth_url)


def _build_creds_payload(creds):
    payload = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    return payload


# OAuth callback (redirect_uri must match Google Cloud Console)
def oauth2callback(request):
    state = request.session.get("state")
    redirect_uri = request.build_absolute_uri(reverse("oauth2callback"))
    flow = get_flow(state=state, redirect_uri=redirect_uri)

    code_verifier = request.session.get("code_verifier")
    if not code_verifier:
        return HttpResponseBadRequest("Missing PKCE code_verifier. Please run Google connect again.")

    flow.fetch_token(
        authorization_response=request.build_absolute_uri(),
        code_verifier=code_verifier,
    )

    # One-time PKCE values; clear them to avoid accidental reuse.
    request.session.pop("code_verifier", None)
    request.session.pop("state", None)

    creds = flow.credentials
    creds_payload = _build_creds_payload(creds)

    # Save globally for the app (singleton-ish).
    DriveAppCredentials.objects.update_or_create(id=1, defaults={"data": creds_payload})

    return redirect("/files/")


def _google_escape_query(s: str) -> str:
    # Escape single quotes for Drive API query syntax.
    return (s or "").replace("'", "\\'")


@user_passes_test(lambda u: u.is_superuser)
@login_required
def admin_dashboard(request):
    """
    Admin dashboard:
    - create Django users (username/password/email, staff/superuser flags)
    - show basic stats (users + Drive connection)
    """
    error = None
    created = False

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""
        email = (request.POST.get("email") or "").strip()
        is_staff = request.POST.get("is_staff") == "on"
        make_superuser = request.POST.get("is_superuser") == "on"

        if not username or not password:
            error = "Username and password are required."
        elif User.objects.filter(username=username).exists():
            error = "A user with that username already exists."
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email or "",
            )
            user.is_staff = is_staff
            user.is_superuser = make_superuser
            if make_superuser:
                user.is_staff = True
            user.save(update_fields=["is_staff", "is_superuser"])
            created = True

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    superusers = User.objects.filter(is_superuser=True).count()

    creds_row = DriveAppCredentials.objects.order_by("-updated_at").first()
    drive_configured = bool(creds_row and creds_row.data)
    drive_updated_at = creds_row.updated_at if creds_row else None

    recent_users = User.objects.order_by("-date_joined")[:8]

    return render(
        request,
        "files/admin_dashboard.html",
        {
            "error": error,
            "created": created,
            "total_users": total_users,
            "active_users": active_users,
            "superusers": superusers,
            "drive_configured": drive_configured,
            "drive_updated_at": drive_updated_at,
            "recent_users": recent_users,
        },
    )


@login_required
def list_files(request):
    service = get_drive_service()
    if not service:
        return render(
            request,
            "files/files.html",
            {
                "drive_configured": False,
                "files": [],
                "q": "",
            },
        )

    q = (request.GET.get("q") or "").strip()
    drive_q = "trashed=false"
    if q:
        drive_q = f"{drive_q} and name contains '{_google_escape_query(q)}'"

    results = (
        service.files()
        .list(
            pageSize=20,
            fields="files(id, name)",
            q=drive_q,
            orderBy="name",
        )
        .execute()
    )

    files = results.get("files", [])

    return render(
        request,
        "files/files.html",
        {
            "drive_configured": True,
            "files": files,
            "q": q,
        },
    )


@login_required
def upload_file(request):
    service = get_drive_service()
    if not service:
        return redirect("/files/")

    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request method.")

    uploaded = request.FILES.get("file")
    if not uploaded:
        return HttpResponseBadRequest("No file uploaded.")

    # `MediaFileUpload` requires a filesystem path.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            for chunk in uploaded.chunks():
                tmp.write(chunk)

        media = MediaFileUpload(
            tmp_path,
            mimetype=getattr(uploaded, "content_type", None) or None,
            resumable=True,
        )

        service.files().create(
            body={"name": uploaded.name},
            media_body=media,
            fields="id",
        ).execute()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return redirect("/files/")


@login_required
def download_file(request, file_id):
    service = get_drive_service()
    if not service:
        return redirect("/files/")

    request_file = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_file)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    fh.seek(0)
    return FileResponse(fh, as_attachment=True, filename="file")