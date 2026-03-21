from django.contrib import admin
from django.contrib.auth.models import User

from .models import DriveAppCredentials, UserFolder, FileAccess, FileActivityLog


@admin.register(DriveAppCredentials)
class DriveAppCredentialsAdmin(admin.ModelAdmin):
    readonly_fields = ['updated_at']


@admin.register(UserFolder)
class UserFolderAdmin(admin.ModelAdmin):
    list_display = ['user', 'folder_id', 'created_at']
    list_filter = ['created_at']


class FileAccessInline(admin.TabularInline):
    model = FileAccess
    extra = 1


@admin.register(FileAccess)
class FileAccessAdmin(admin.ModelAdmin):
    list_display = ['name', 'file_id', 'folder_id', 'user', 'can_read', 'can_write', 'created_at']
    list_filter = ['can_read', 'can_write', 'folder_id', 'created_at']
    inlines = []


@admin.register(FileActivityLog)
class FileActivityLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'file_name', 'timestamp']
    list_filter = ['action', 'timestamp']
    date_hierarchy = 'timestamp'
    readonly_fields = ['timestamp']


admin.site.unregister(User)
