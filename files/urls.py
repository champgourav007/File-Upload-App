from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Admin-only Google connect (one-time setup)
    path("google/connect/", views.google_login, name="google_connect"),
    path("oauth2callback/", views.oauth2callback, name="oauth2callback"),

    path("files/", views.list_files, name="files"),
    path("upload/", views.upload_file, name="upload"),
    path("download/<str:file_id>/", views.download_file, name="download"),
]