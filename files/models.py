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

class UserFolder(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    folder_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s folder ({self.folder_id})"


class FileAccess(models.Model):
    """Admin-managed file access control."""
    file_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=False)
    folder_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['file_id', 'user']

    def __str__(self):
        return f"{self.name} → {self.user.username}"


class FileActivityLog(models.Model):
    """Track uploads/downloads for admin stats."""
    ACTION_CHOICES = [
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('view', 'View'),
    ]
    
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    file_id = models.CharField(max_length=100, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} - {self.timestamp}"
