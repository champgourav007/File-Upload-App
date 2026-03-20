from django.db import models


class DriveAppCredentials(models.Model):
    """
    Stores a single set of OAuth credentials for accessing Google Drive.

    This lets normal (Django) users upload/search/download without requiring
    them to run the Google OAuth consent flow every time.

    Admins must connect once via the Google connect flow.
    """

    # Singleton-ish: we will treat the row with pk=1 as the active credentials.
    data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"DriveAppCredentials(updated_at={self.updated_at})"
