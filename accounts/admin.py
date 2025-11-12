from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Request Hub",
            {
                "fields": (
                    "role",
                    "phone_number",
                    "profile_photo",
                    "profile_completed",
                )
            },
        ),
    )
    list_display = ("username", "email", "role", "is_active", "profile_completed")
    list_filter = ("role", "is_active")
