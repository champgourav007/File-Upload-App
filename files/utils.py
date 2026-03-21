import os

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from .models import DriveAppCredentials

SCOPES = ['https://www.googleapis.com/auth/drive']
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')


def get_user_folder(service, user):
    """
    Get or create user's private folder in Drive.
    """
    from .models import UserFolder
    
    try:
        user_folder = UserFolder.objects.get(user=user)
        folder_id = user_folder.folder_id
    except UserFolder.DoesNotExist:
        # Create folder
        folder_metadata = {
            'name': f"{user.username}'s Files",
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': []  # Root
        }
        folder = service.files().create(body=folder_metadata, fields='id').execute()
        folder_id = folder.get('id')
        
        # Save
        UserFolder.objects.create(user=user, folder_id=folder_id)
    
    return folder_id


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