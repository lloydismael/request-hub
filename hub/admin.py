from django.contrib import admin

from .models import Account, Notification, Request, StatusLog


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ("name", "created_at")


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code",
        "account",
        "account_manager",
        "priority",
        "status",
        "due_date",
    )
    list_filter = ("priority", "status", "product_category", "engagement_type")
    search_fields = ("reference_code", "account__name", "account_manager")
    autocomplete_fields = ("requestor", "account", "engineer")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "message", "created_at", "is_read")
    list_filter = ("is_read",)
    search_fields = ("message", "recipient__username")


@admin.register(StatusLog)
class StatusLogAdmin(admin.ModelAdmin):
    list_display = ("request", "author", "created_at")
    list_filter = ("created_at",)
    search_fields = ("request__reference_code", "author__username", "message")
