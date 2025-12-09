from django.urls import path

from .views import (
    DashboardView,
    NotificationListView,
    NotificationFollowRedirectView,
    NotificationReadView,
    NotificationDeleteView,
    RequestAdminUpdateView,
    RequestDeleteView,
    RequestDetailView,
    RequestExportCSVView,
    RequestNudgeView,
    RequestOutlookRedirectView,
    RequestStatusUpdateView,
    RequestTeamsRedirectView,
    RequestUpdateView,
    RequestReportView,
    UserManagementView,
    RequestCollaborativeManageView,
)

app_name = "hub"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("requests/export/csv/", RequestExportCSVView.as_view(), name="request-export"),
    path("requests/<int:pk>/", RequestDetailView.as_view(), name="request-detail"),
    path("requests/<int:pk>/edit/", RequestUpdateView.as_view(), name="request-edit"),
    path("requests/<int:pk>/status/", RequestStatusUpdateView.as_view(), name="request-status"),
    path("requests/<int:pk>/manage/", RequestAdminUpdateView.as_view(), name="request-manage"),
    path("requests/<int:pk>/manage/collab/", RequestCollaborativeManageView.as_view(), name="request-manage-collab"),
    path("requests/<int:pk>/nudge/", RequestNudgeView.as_view(), name="request-nudge"),
    path("requests/<int:pk>/teams-chat/", RequestTeamsRedirectView.as_view(), name="request-teams"),
    path("requests/<int:pk>/outlook/", RequestOutlookRedirectView.as_view(), name="request-outlook"),
    path("requests/<int:pk>/delete/", RequestDeleteView.as_view(), name="request-delete"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path("notifications/<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("notifications/<int:pk>/follow/", NotificationFollowRedirectView.as_view(), name="notification-follow"),
    path("notifications/<int:pk>/delete/", NotificationDeleteView.as_view(), name="notification-delete"),
    path("management/", UserManagementView.as_view(), name="management"),
    path("reports/", RequestReportView.as_view(), name="report"),
]
