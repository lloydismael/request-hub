from django.urls import path

from .views import ProfileUpdateView

app_name = "accounts"

urlpatterns = [
    path("profile/", ProfileUpdateView.as_view(), name="update"),
]
