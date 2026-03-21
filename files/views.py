import io
import os
import tempfile

import django
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.http import FileResponse, HttpResponseBadRequest
from django.urls import reverse
from django.utils import timezone
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

from .models import DriveAppCredentials, FileAccess, FileActivityLog
from .utils import get_flow, get_drive_service, get_user_folder


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
        include_granted_scopes="true",
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
    - create Django users
    - file management & stats
    """
    error = None
    created = False

    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "create_user":
            username = (request.POST.get("username") or "").strip()
            password = request.POST.get("password") or ""
            email = (request.POST.get("email") or "").strip()
            is_staff = request.POST.get("is_staff") == "on"
            make_superuser = request.POST.get("is_superuser") == "on"

            if not username or not password:
                error = "Username and password are required."
            elif User.objects.filter(username=username).exists():
                error = "Username already exists."
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
                
        elif action == "toggle_access":
            file_id = request.POST.get("file_id")
            user_id = request.POST.get("user_id")
            permission = request.POST.get("permission")  # 'read' or 'write'
            
            access, created = FileAccess.objects.get_or_create(
                file_id=file_id, 
                user_id=user_id,
                defaults={'name': request.POST.get("file_name", 'Unknown')}
            )
            # Fetch folder_id from Drive if not set
            if not access.folder_id:
                service = get_drive_service()
                if service:
                    try:
                        file_metadata = service.files().get(
                            fileId=file_id, 
                            fields='parents'
                        ).execute()
                        parents = file_metadata.get('parents', [])
                        if parents:
                            access.folder_id = parents[0]  # Use first parent (primary folder)
                    except Exception:
                        pass  # Fail silently if Drive unavailable
            if permission == 'read':
                access.can_read = not access.can_read
            else:
                access.can_write = not access.can_write
            access.save()
    
    # User stats
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    superusers = User.objects.filter(is_superuser=True).count()
    recent_users = User.objects.order_by("-date_joined")[:8]

    # Drive status
    creds_row = DriveAppCredentials.objects.order_by("-updated_at").first()
    drive_configured = bool(creds_row and creds_row.data)
    drive_updated_at = creds_row.updated_at if creds_row else None

    # All Drive files (admin sees everything)
    service = get_drive_service()
    all_files = []
    if service:
        try:
            results = service.files().list(
                pageSize=50,
                fields="files(id, name, mimeType, parents)",
                q="trashed=false"
            ).execute()
            all_files = results.get("files", [])
        except Exception:
            pass  # Graceful if Drive down

    # File accesses - now with folder_id context
    file_accesses = FileAccess.objects.select_related('user').order_by('-created_at')[:20]

    # Activity stats
    activity_stats = {
        'total_uploads': FileActivityLog.objects.filter(action='upload').count(),
        'total_downloads': FileActivityLog.objects.filter(action='download').count(),
        'total_actions': FileActivityLog.objects.count(),
        'recent_logs': FileActivityLog.objects.select_related('user').order_by('-timestamp')[:10],
        'uploads_today': FileActivityLog.objects.filter(
            action='upload',
            timestamp__date=django.utils.timezone.now().date()
        ).count(),
        'downloads_today': FileActivityLog.objects.filter(
            action='download',
            timestamp__date=django.utils.timezone.now().date()
        ).count(),
    }

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
            "all_files": all_files,
            "file_accesses": file_accesses,
            "activity_stats": activity_stats,
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
    
    # Build query - user's folder + shared files they can access
    user_folder_id = get_user_folder(service, request.user)
    base_q = f"'{user_folder_id}' in parents and trashed=false"
    
    # Add admin-accessible files from other folders - now using folder_id context
    user_accesses = FileAccess.objects.filter(
        user=request.user, 
        can_read=True
    ).select_related('user')
    user_access_files = [access.file_id for access in user_accesses if access.file_id != user_folder_id]
    user_file_access = [fid for fid in user_access_files]
    
    # Optionally group by folder_id for future tree views
    folder_accesses = {}
    for access in user_accesses:
        if access.folder_id and access.file_id != user_folder_id:
            if access.folder_id not in folder_accesses:
                folder_accesses[access.folder_id] = []
            folder_accesses[access.folder_id].append(access.file_id)
    
    if user_file_access:
        # shared_q_parts = [f"id = '{fid}'" for fid in user_file_access]
        # base_q = f"({base_q}) or ({' or '.join(shared_q_parts)})"
        pass
    
    if q:
        base_q += f" and name contains '{_google_escape_query(q)}'"

    print(f"Drive query for {request.user.username}: {base_q}")  # Debug
    print(f"User access files: {user_access_files}")  # Debug
    print(f"Folder accesses: {folder_accesses}")  # Debug
    
    results = (
        service.files()
        .list(
            pageSize=50,
            fields="files(id, name, mimeType, thumbnailLink, webViewLink)",
            q=base_q,
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
            "folder_accesses": folder_accesses,  # Pass for template use
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

    # Get/create user folder
    user_folder_id = get_user_folder(service, request.user)

    # Direct in-memory upload to user folder
    media = MediaIoBaseUpload(
        io.BytesIO(uploaded.read()),
        mimetype=uploaded.content_type,
        resumable=False
    )

    service.files().create(
        body={
            "name": uploaded.name,
            "parents": [user_folder_id]
        },
        media_body=media,
        fields="id",
    ).execute()

    return redirect("/files/")


@login_required
def download_file(request, file_id):
    service = get_drive_service()
    if not service:
        return redirect("/files/")

    # Get file metadata for correct name
    file_metadata = service.files().get(fileId=file_id, fields='name').execute()
    filename = file_metadata.get('name', 'file')

    request_file = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request_file)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        if status:
            print(f"Download progress: {int(status.progress() * 100)}%")

    fh.seek(0)
    response = FileResponse(fh, as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Type'] = 'application/octet-stream'
    return response
