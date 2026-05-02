from __future__ import annotations

from typing import Dict

from django.conf import settings
from django.http import HttpRequest

from accounts.models import User


def notification_badges(request: HttpRequest) -> Dict[str, int]:
    """Provide global notification badge counts for the navigation bar."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"new_ticket_count": 0, "app_version": settings.APP_VERSION}

    if getattr(user, "role", None) not in {User.Roles.ADMIN, User.Roles.PM_ESG}:
        return {"new_ticket_count": 0, "app_version": settings.APP_VERSION}

    new_ticket_count = (
        user.notifications.filter(is_read=False, source__icontains="new request").count()
    )
    return {"new_ticket_count": new_ticket_count, "app_version": settings.APP_VERSION}
