from django.urls import path

from .views import (
    DashboardView,
    NotificationListView,
    NotificationReadView,
    RequestAdminUpdateView,
    RequestDeleteView,
    RequestNudgeView,
    RequestDetailView,
)

app_name = "hub"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("requests/<int:pk>/", RequestDetailView.as_view(), name="request-detail"),
    path("requests/<int:pk>/manage/", RequestAdminUpdateView.as_view(), name="request-manage"),
    path("requests/<int:pk>/nudge/", RequestNudgeView.as_view(), name="request-nudge"),
    path("requests/<int:pk>/delete/", RequestDeleteView.as_view(), name="request-delete"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("notifications/<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
]
