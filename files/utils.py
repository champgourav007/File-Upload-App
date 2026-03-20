import os

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from .models import DriveAppCredentials

SCOPES = ['https://www.googleapis.com/auth/drive']
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')


def get_flow(state=None, redirect_uri=None):
    """
    Build OAuth flow.

    redirect_uri must match one of the redirect URIs configured for your OAuth client
    (in Google Cloud Console / credentials.json).
    """
    redirect_uri = redirect_uri or "http://localhost:8000/oauth2callback/" or "https://breakfast-writes-belong-saturn.trycloudflare.com/oauth2callback/"
    return Flow.from_client_secrets_file(
        CREDENTIALS_PATH,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        state=state,
    )


def get_drive_service():
    creds_row = DriveAppCredentials.objects.order_by("-updated_at").first()
    if not creds_row or not creds_row.data:
        return None

    creds = Credentials(**creds_row.data)
    return build("drive", "v3", credentials=creds)