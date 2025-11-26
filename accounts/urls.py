from django.urls import path

from .views import ProfileUpdateView, StoredFileServeView

app_name = "accounts"

urlpatterns = [
    path("profile/", ProfileUpdateView.as_view(), name="update"),
    path("media/<path:name>", StoredFileServeView.as_view(), name="media"),
]
