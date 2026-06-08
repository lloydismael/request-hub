from django.urls import path

from .views import BackupDataView, ProfileUpdateView, RestoreDataView, StoredFileServeView

app_name = "accounts"

urlpatterns = [
    path("profile/", ProfileUpdateView.as_view(), name="update"),
    path("media/<path:name>", StoredFileServeView.as_view(), name="media"),
    path("backup/", BackupDataView.as_view(), name="backup"),
    path("restore/", RestoreDataView.as_view(), name="restore"),
]
