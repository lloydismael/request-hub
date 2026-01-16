import csv
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Min, Q, Sum
from django.forms import modelformset_factory
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, DeleteView, ListView, TemplateView, UpdateView
from urllib.parse import quote

from accounts.forms import UserManagementForm
from accounts.models import User

from .forms import (
    AccountManagementForm,
    AdminRequestFilterForm,
    EngineerActivityLogForm,
    RequestAdminForm,
    RequestForm,
    RequestStatusForm,
    StatusLogForm,
)
from .constants import ACCOUNT_NAME_RAW
from .models import (
    Account,
    EngineerActivityLog,
    Notification,
    Request,
    RequestCommunication,
    StatusLog,
)
from .mixins import AdminRequiredMixin, AdminOrEngineerRequiredMixin, EngineerRequiredMixin

MANILA_TZ = ZoneInfo("Asia/Manila")


class EngineerActivityLogView(EngineerRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "hub/activity_logs.html"
    form_class = EngineerActivityLogForm

    def get_queryset(self):
        return (
            EngineerActivityLog.objects.filter(engineer=self.request.user)
            .select_related("account", "request")
            .order_by("-request_date", "-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get("form")
        logs = kwargs.get("logs")
        editing_log = kwargs.get("editing_log")
        if form is None:
            form = self.form_class(engineer=self.request.user)
        if logs is None:
            logs = list(self.get_queryset())
        else:
            logs = list(logs)

        total_hours = Decimal("0")
        billable_hours = Decimal("0")
        for log in logs:
            hours = log.actual_hours or Decimal("0")
            total_hours += hours
            if log.is_billable:
                billable_hours += hours

        context.update(
            {
                "form": form,
                "logs": logs,
                "hours_summary": {
                    "total": total_hours,
                    "billable": billable_hours,
                    "non_billable": total_hours - billable_hours,
                },
                "editing_log": editing_log,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        edit_id = request.GET.get("edit")
        editing_log = None
        form = None
        if edit_id:
            try:
                editing_log = self.get_queryset().get(pk=edit_id)
            except (EngineerActivityLog.DoesNotExist, ValueError):
                messages.error(request, "We could not find that activity log to edit.")
                return redirect("hub:activity-logs")
            form = self.form_class(engineer=request.user, instance=editing_log)
        context = self.get_context_data(form=form, editing_log=editing_log)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        log_id = request.POST.get("log_id")
        instance = None
        if log_id:
            try:
                instance = self.get_queryset().get(pk=log_id)
            except (EngineerActivityLog.DoesNotExist, ValueError):
                messages.error(request, "Unable to update the selected activity log.")
                return redirect("hub:activity-logs")

        form = self.form_class(data=request.POST, engineer=request.user, instance=instance)
        if form.is_valid():
            activity_log = form.save(commit=False)
            activity_log.engineer = request.user
            activity_log.save()
            if instance:
                messages.success(request, "Activity log updated successfully.")
            else:
                messages.success(request, "Activity logged successfully.")
            return redirect("hub:activity-logs")
        logs = self.get_queryset()
        context = self.get_context_data(form=form, logs=logs, editing_log=instance)
        return self.render_to_response(context)


class EngineerActivityLogDeleteView(EngineerRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        log = get_object_or_404(
            EngineerActivityLog.objects.filter(engineer=request.user),
            pk=pk,
        )
        log.delete()
        messages.success(request, "Activity log deleted successfully.")
        return redirect("hub:activity-logs")


class ReportExportView(AdminRequiredMixin, LoginRequiredMixin, View):
    """Export operational or activity report data as CSV."""

    def get(self, request, *args, **kwargs):
        report_view = (request.GET.get("report_view") or "operational").lower()
        if report_view == "activity":
            return self._export_activity_logs()
        return self._export_operational_report()

    @staticmethod
    def _format_user(user: Optional[User]) -> str:
        if not user:
            return ""
        full_name = user.get_full_name()
        return full_name or user.username

    @staticmethod
    def _format_date(value):
        if not value:
            return ""
        return value.strftime("%Y-%m-%d")

    @staticmethod
    def _format_datetime(value):
        if not value:
            return ""
        localized = timezone.localtime(value)
        return localized.strftime("%Y-%m-%d %H:%M:%S")

    def _export_operational_report(self):
        filename = f"operational-report-{timezone.now().strftime('%Y%m%d-%H%M%S')}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Reference",
                "Requestor",
                "Account",
                "Engagement",
                "Product Category",
                "Priority",
                "Status",
                "Engineer",
                "Backup Engineer",
                "Start Date",
                "Due Date",
                "Created",
            ]
        )

        queryset = (
            Request.objects.select_related("requestor", "account", "engineer", "backup_engineer")
            .order_by("created_at")
        )
        status_labels = dict(Request.Status.choices)
        engagement_labels = dict(Request.Engagement.choices)
        for request_obj in queryset:
            writer.writerow(
                [
                    request_obj.reference_code,
                    self._format_user(getattr(request_obj, "requestor", None)),
                    request_obj.account.name if request_obj.account else "",
                    engagement_labels.get(request_obj.engagement_type, request_obj.engagement_type or ""),
                    request_obj.product_category or "",
                    request_obj.get_priority_display(),
                    status_labels.get(request_obj.status, request_obj.status or ""),
                    self._format_user(getattr(request_obj, "engineer", None)),
                    self._format_user(getattr(request_obj, "backup_engineer", None)),
                    self._format_date(request_obj.start_date),
                    self._format_date(request_obj.due_date),
                    self._format_datetime(request_obj.created_at),
                ]
            )

        return response

    def _export_activity_logs(self):
        filename = f"activity-logs-{timezone.now().strftime('%Y%m%d-%H%M%S')}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Request Date",
                "Engineer",
                "Account",
                "Request Reference",
                "Activity Type",
                "Details",
                "Hours",
                "Location",
                "Billable",
                "Created",
            ]
        )

        logs = (
            EngineerActivityLog.objects.select_related("engineer", "account", "request")
            .order_by("-request_date", "-created_at")
        )
        activity_labels = dict(EngineerActivityLog.ActivityType.choices)
        location_labels = dict(EngineerActivityLog.Location.choices)
        for log in logs:
            writer.writerow(
                [
                    self._format_date(log.request_date),
                    self._format_user(log.engineer),
                    log.account.name if log.account else "",
                    log.request.reference_code if log.request else "",
                    activity_labels.get(log.activity_type, log.activity_type or ""),
                    log.details or "",
                    f"{log.actual_hours}",
                    location_labels.get(log.location, log.location or ""),
                    "Yes" if log.is_billable else "No",
                    self._format_datetime(log.created_at),
                ]
            )

        return response


def summarize_request_changes(original, updated, changed_fields):
    field_labels = {
        "account": "Account",
        "priority": "Priority",
        "status": "Status",
        "due_date": "Due date",
        "end_date": "End date",
        "engineer": "Engineer",
        "backup_engineer": "Backup engineer",
        "account_manager": "Requestor",
        "description": "Description",
        "engagement_type": "Engagement type",
        "product_category": "Product category",
        "start_date": "Start date",
    }

    choice_maps = {
        "priority": dict(Request.Priority.choices),
        "status": dict(Request.Status.choices),
        "engagement_type": dict(Request.Engagement.choices),
    }

    def format_value(field, value):
        if field in choice_maps:
            return choice_maps[field].get(value, "Not set") if value else "Not set"
        if field in {"due_date", "end_date", "start_date"}:
            return value.strftime("%b %d, %Y") if value else "Not set"
        if field == "account":
            return value.name if value else "Not set"
        if field in {"engineer", "backup_engineer"}:
            if value:
                return value.get_full_name() or value.username
            return "Unassigned"
        if value is None or value == "":
            return "Not set"
        return str(value)

    change_summaries = []
    for field in changed_fields:
        if field not in field_labels:
            continue
        old_value = getattr(original, field, None)
        new_value = getattr(updated, field, None)
        if old_value == new_value:
            continue
        old_display = format_value(field, old_value)
        new_display = format_value(field, new_value)
        label = field_labels[field]
        change_summaries.append(f"{label}: {old_display} → {new_display}")

    return "; ".join(change_summaries)


def notify_status_update(log, source_label):
    """Notify relevant stakeholders that a new status update was posted."""
    request_obj = log.request
    author = log.author
    author_name = author.get_full_name() or author.username

    recipients: dict[int, User] = {}
    if request_obj.engineer:
        recipients[request_obj.engineer.pk] = request_obj.engineer
    if request_obj.requestor:
        recipients[request_obj.requestor.pk] = request_obj.requestor

    for admin in User.objects.filter(role=User.Roles.ADMIN):
        recipients[admin.pk] = admin

    recipients.pop(author.pk, None)

    for user in recipients.values():
        Notification.objects.create(
            recipient=user,
            message=f"{author_name} posted an update on {request_obj.reference_code or 'a request'}.",
            related_request=request_obj,
            actor=author_name,
            source=source_label,
        )


def create_change_status_log(request_obj: Request, actor_user: User, source_label: str, summary_text: str) -> None:
    """Persist a status log entry describing automatic updates."""
    if not summary_text:
        return

    actor_name = actor_user.get_full_name() or actor_user.username
    message = f"{actor_name} updated the request ({source_label}): {summary_text}"
    StatusLog.objects.create(
        request=request_obj,
        author=actor_user,
        message=message,
    )


def normalize_request_form_changed_fields(changed_fields):
    normalized = []
    for field in changed_fields:
        if field == "needed_by":
            normalized.append("start_date")
        elif field == "account_name":
            continue
        else:
            normalized.append(field)
    return normalized


def notify_account_manager_request_update(actor_user, original, updated, changed_fields, source_label):
    summary_text = summarize_request_changes(original, updated, changed_fields)
    if not summary_text:
        return

    create_change_status_log(updated, actor_user, source_label, summary_text)

    actor = actor_user.get_full_name() or actor_user.username
    recipients: dict[int, User] = {}

    for admin in User.objects.filter(role=User.Roles.ADMIN):
        recipients[admin.pk] = admin
    if updated.requestor:
        recipients[updated.requestor.pk] = updated.requestor
    if updated.engineer:
        recipients[updated.engineer.pk] = updated.engineer
    if updated.backup_engineer:
        recipients[updated.backup_engineer.pk] = updated.backup_engineer

    recipients.pop(actor_user.pk, None)

    for recipient in recipients.values():
        Notification.objects.create(
            recipient=recipient,
            message=f"{actor} updated {updated.reference_code}: {summary_text}",
            related_request=updated,
            actor=actor,
            source=source_label,
        )


def notify_engineer_assignment_email(
    request_obj: Request,
    *,
    actor_user: User,
    request=None,
    previous_engineer_id: int | None = None,
    previous_backup_id: int | None = None,
) -> None:
    """Email the assigned engineer or backup when they receive a request."""

    recipients: list[str] = []

    if request_obj.engineer_id and request_obj.engineer_id != previous_engineer_id:
        email = (request_obj.engineer.email or "").strip()
        if email:
            recipients.append(email)

    if request_obj.backup_engineer_id and request_obj.backup_engineer_id != previous_backup_id:
        email = (request_obj.backup_engineer.email or "").strip()
        if email:
            recipients.append(email)

    if not recipients:
        return

    actor_name = actor_user.get_full_name() or actor_user.username or "Request Hub"
    due_display = request_obj.due_date.strftime("%b %d, %Y") if request_obj.due_date else "Not set"
    detail_url = ""

    if request:
        try:
            detail_url = request.build_absolute_uri(request_obj.get_absolute_url())
        except Exception:
            detail_url = ""

    subject = f"[Request Hub] New assignment - {request_obj.reference_code or 'Request'}"
    body_lines = [
        "You have been assigned a request in Request Hub.",
        "",
        f"Reference: {request_obj.reference_code or 'Request'}",
        f"Account: {request_obj.account.name if request_obj.account else 'Not set'}",
        f"Engagement: {request_obj.get_engagement_type_display()}",
        f"Priority: {request_obj.get_priority_display()}",
        f"Due date: {due_display}",
        f"Assigned by: {actor_name}",
    ]

    description = (request_obj.description or "").strip()
    if description:
        body_lines.extend(["", "Description:", description])

    if detail_url:
        body_lines.extend(["", f"View request: {detail_url}"])

    send_mail(
        subject,
        "\n".join(body_lines),
        settings.DEFAULT_FROM_EMAIL,
        recipients,
        fail_silently=True,
    )


def _admin_sort_account_manager_key(request_obj):
    manager_name = ""
    manager_user = getattr(request_obj, "requestor", None)
    if manager_user:
        manager_name = (manager_user.get_full_name() or manager_user.username or "").strip()
    elif request_obj.account_manager:
        manager_name = request_obj.account_manager.strip()
    normalized = manager_name.lower()
    has_name = 0 if normalized else 1
    return (has_name, normalized)


def _admin_sort_engineer_key(request_obj):
    engineer = getattr(request_obj, "engineer", None)
    if engineer:
        engineer_name = (engineer.get_full_name() or engineer.username or "").strip().lower()
        return (0, engineer_name)
    return (1, "")


def _admin_sort_date_key(value):
    if value is None:
        return (1, date.max)
    return (0, value)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "hub/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["role"] = user.role
        context["notifications"] = user.notifications.filter(is_read=False)[:10]

        if user.role == User.Roles.REQUESTOR:
            form = kwargs.get("form")
            if form is None:
                form = RequestForm(actor_role=User.Roles.REQUESTOR)
            context["form"] = form
            context["account_name_choices"] = form.account_name_suggestions
            metric_filter = self.request.GET.get("metric_filter") or ""
            metric_keys = {"ongoing", "completed"}
            if metric_filter not in metric_keys:
                metric_filter = ""

            requests = list(
                Request.objects.filter(requestor=user)
                .select_related("account", "engineer")
                .order_by("-created_at")
            )

            metrics = {
                "ongoing": sum(1 for req in requests if req.status == Request.Status.ONGOING),
                "completed": sum(1 for req in requests if req.status == Request.Status.COMPLETED),
            }

            filtered_requests = requests
            if metric_filter == "ongoing":
                filtered_requests = [req for req in requests if req.status == Request.Status.ONGOING]
            elif metric_filter == "completed":
                filtered_requests = [req for req in requests if req.status == Request.Status.COMPLETED]

            metric_links = {}
            for key in ["ongoing", "completed"]:
                params = self.request.GET.copy()
                if params.get("metric_filter") == key:
                    params.pop("metric_filter", None)
                else:
                    params["metric_filter"] = key
                encoded = params.urlencode()
                metric_links[key] = f"?{encoded}" if encoded else "?"

            context["requests"] = filtered_requests
            context["metrics"] = metrics
            context["metric_links"] = metric_links
            context["active_metric_filter"] = metric_filter
            context["form_has_errors"] = form.is_bound and bool(form.errors)
        elif user.role == User.Roles.ENGINEER:
            metric_filter = self.request.GET.get("metric_filter") or ""
            valid_metrics = {"ongoing", "due_soon", "overdue", "completed"}
            if metric_filter not in valid_metrics:
                metric_filter = ""

            requests = list(
                Request.objects.filter(engineer=user)
                .select_related("account", "requestor")
                .order_by("status", "due_date")
            )

            request_ids = [req.pk for req in requests]
            outlook_limited: set[int] = set()
            teams_limited: set[int] = set()
            if request_ids:
                communications = RequestCommunication.objects.filter(
                    request_id__in=request_ids,
                    user=user,
                ).only("request_id", "channel")
                for comm in communications:
                    if comm.channel == RequestCommunication.Channel.OUTLOOK:
                        outlook_limited.add(comm.request_id)
                    elif comm.channel == RequestCommunication.Channel.TEAMS:
                        teams_limited.add(comm.request_id)
            for req in requests:
                setattr(req, "outlook_limit_reached", req.pk in outlook_limited)
                setattr(req, "teams_limit_reached", req.pk in teams_limited)

            today = timezone.now().astimezone(MANILA_TZ).date()
            metrics = {
                "ongoing": sum(1 for req in requests if req.status == Request.Status.ONGOING),
                "due_soon": sum(
                    1
                    for req in requests
                    if req.status == Request.Status.ONGOING
                    and req.due_date
                    and 0 <= (req.due_date - today).days <= 3
                ),
                "overdue": sum(
                    1
                    for req in requests
                    if req.status == Request.Status.ONGOING and req.due_date and req.due_date < today
                ),
                "completed": sum(1 for req in requests if req.status == Request.Status.COMPLETED),
            }

            filtered_requests = requests
            if metric_filter == "ongoing":
                filtered_requests = [req for req in requests if req.status == Request.Status.ONGOING]
            elif metric_filter == "due_soon":
                filtered_requests = [
                    req
                    for req in requests
                    if req.status == Request.Status.ONGOING
                    and req.due_date
                    and 0 <= (req.due_date - today).days <= 3
                ]
            elif metric_filter == "overdue":
                filtered_requests = [
                    req
                    for req in requests
                    if req.status == Request.Status.ONGOING and req.due_date and req.due_date < today
                ]
            elif metric_filter == "completed":
                filtered_requests = [req for req in requests if req.status == Request.Status.COMPLETED]

            metric_links = {}
            for key in ("ongoing", "due_soon", "overdue", "completed"):
                params = self.request.GET.copy()
                if params.get("metric_filter") == key:
                    params.pop("metric_filter", None)
                else:
                    params["metric_filter"] = key
                encoded = params.urlencode()
                metric_links[key] = f"?{encoded}" if encoded else "?"

            context["requests"] = filtered_requests
            context["metrics"] = metrics
            context["metric_links"] = metric_links
            context["active_metric_filter"] = metric_filter
        else:
            metric_keys = [
                "open",
                "overdue",
                "due_soon",
                "completed",
                "new_this_week",
            ]
            metric_filter = self.request.GET.get("metric_filter")
            if not metric_filter or metric_filter not in metric_keys:
                metric_filter = "open"

            queryset = Request.objects.select_related("account", "engineer", "requestor")
            filter_form = AdminRequestFilterForm(self.request.GET or None)
            filtered_queryset = filter_form.filter_queryset(queryset)
            requests = filter_form.filter_sequence(filtered_queryset)
            filters_active = filter_form.has_active_filters()
            show_filters = self.request.GET.get("show_filters") == "1"

            if not isinstance(requests, list):
                requests = list(requests)

            sort_map = {
                "reference_code": lambda req: (req.reference_code or "").lower(),
                "account": lambda req: (req.account.name.lower() if req.account else ""),
                "account_manager": _admin_sort_account_manager_key,
                "engineer": _admin_sort_engineer_key,
                "engagement": lambda req: req.engagement_type or "",
                "status": lambda req: req.status or "",
                "created": lambda req: req.created_at,
                "end_date": lambda req: _admin_sort_date_key(req.end_date),
                "days": lambda req: req.days_since_creation,
                "due": lambda req: _admin_sort_date_key(req.due_date),
            }

            default_sort = "created"
            default_direction = "desc"
            sort_key = self.request.GET.get("sort", default_sort)
            direction = self.request.GET.get("direction", default_direction)
            if sort_key not in sort_map:
                sort_key = default_sort
            if direction not in {"asc", "desc"}:
                direction = default_direction
            reverse = direction == "desc"

            key_fn = sort_map[sort_key]
            requests.sort(key=key_fn, reverse=reverse)

            null_field_map = {"end_date": "end_date", "due": "due_date"}
            if sort_key in null_field_map:
                field_name = null_field_map[sort_key]
                ordered = [req for req in requests if getattr(req, field_name) is not None]
                ordered.extend(req for req in requests if getattr(req, field_name) is None)
                requests = ordered

            self._annotate_acknowledgement_status(requests)

            today = timezone.now().astimezone(MANILA_TZ).date()
            all_requests = list(requests)
            filtered_requests = self._filter_requests_by_metric(all_requests, metric_filter, today)

            overdue_count = sum(1 for req in all_requests if req.admin_days_overdue)
            status_counts = {
                "all": len(all_requests),
                "ongoing": sum(1 for req in all_requests if req.status == Request.Status.ONGOING),
                "completed": sum(1 for req in all_requests if req.status == Request.Status.COMPLETED),
            }

            columns = list(sort_map.keys())
            next_directions = {}
            for column in columns:
                if column == sort_key:
                    next_directions[column] = "asc" if direction == "desc" else "desc"
                else:
                    next_directions[column] = "asc"

            base_params = self.request.GET.copy()
            base_params.pop("sort", None)
            base_params.pop("direction", None)
            sort_links = {}
            for column in columns:
                params = base_params.copy()
                params["sort"] = column
                params["direction"] = next_directions[column]
                encoded = params.urlencode()
                sort_links[column] = f"?{encoded}" if encoded else "?"

            toggle_params = self.request.GET.copy()
            if show_filters:
                toggle_params.pop("show_filters", None)
            else:
                toggle_params["show_filters"] = "1"
            toggle_encoded = toggle_params.urlencode()
            filter_toggle_link = f"?{toggle_encoded}" if toggle_encoded else ("?" if show_filters else "?show_filters=1")

            metric_links = {}
            metric_buckets = {}
            for key in metric_keys:
                params = self.request.GET.copy()
                if params.get("metric_filter") == key:
                    params.pop("metric_filter", None)
                else:
                    params["metric_filter"] = key
                encoded_params = params.urlencode()
                metric_links[key] = f"?{encoded_params}" if encoded_params else "?"
                metric_buckets[key] = self._filter_requests_by_metric(all_requests, key, today)

            context["requests"] = filtered_requests
            context["overdue_count"] = overdue_count
            context["status_counts"] = status_counts
            context["new_ticket_count"] = user.notifications.filter(
                is_read=False,
                source__icontains="new request",
            ).count()
            context["current_sort"] = sort_key
            context["current_direction"] = direction
            context["sort_next"] = next_directions
            context["sort_links"] = sort_links
            context["filter_form"] = filter_form
            context["filters_active"] = filters_active or (metric_filter and metric_filter != "open")
            context["show_filters"] = show_filters
            context["filter_toggle_link"] = filter_toggle_link
            context["metrics"] = {key: len(metric_buckets[key]) for key in metric_keys}
            context["metric_links"] = metric_links
            context["active_metric_filter"] = metric_filter
        return context

    @staticmethod
    def _filter_requests_by_metric(requests: list[Request], metric_filter: str, today: date) -> list[Request]:
        if not metric_filter:
            return requests

        if metric_filter == "open":
            return [req for req in requests if req.status == Request.Status.ONGOING]
        if metric_filter == "overdue":
            return [
                req
                for req in requests
                if req.admin_days_overdue
            ]
        if metric_filter == "due_soon":
            return [
                req
                for req in requests
                if req.due_date and 0 <= (req.due_date - today).days <= 3
            ]
        if metric_filter == "completed":
            return [
                req
                for req in requests
                if req.status == Request.Status.COMPLETED
            ]
        if metric_filter == "new_this_week":
            return [
                req
                for req in requests
                if (today - req.created_at.date()).days <= 7
            ]
        return requests

    @staticmethod
    def _format_duration(delta: timedelta) -> str:
        total_seconds = int(delta.total_seconds())
        if total_seconds <= 0:
            return "<1 minute"
        minutes = total_seconds // 60
        if minutes < 1:
            return "<1 minute"
        hours, rem_minutes = divmod(minutes, 60)
        parts = []
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if rem_minutes:
            parts.append(f"{rem_minutes} minute{'s' if rem_minutes != 1 else ''}")
        if not parts:
            return "<1 minute"
        return " ".join(parts)

    def _annotate_acknowledgement_status(self, requests: list[Request]) -> None:
        if not requests:
            return
        request_ids = [req.pk for req in requests if req.pk]
        if not request_ids:
            return

        ack_rows = (
            RequestCommunication.objects.filter(
                request_id__in=request_ids,
                user__role__in=[User.Roles.ENGINEER, User.Roles.ADMIN],
                channel__in=[
                    RequestCommunication.Channel.OUTLOOK,
                    RequestCommunication.Channel.TEAMS,
                ],
            )
            .values("request_id")
            .annotate(first_ack=Min("created_at"))
        )
        ack_map = {row["request_id"]: row["first_ack"] for row in ack_rows}

        now = timezone.now()
        amber_threshold = timedelta(minutes=45)
        sla_threshold = timedelta(hours=1)

        for req in requests:
            ack_time = ack_map.get(req.pk)
            status = ""
            tooltip = ""
            if ack_time:
                delta = ack_time - req.created_at
                if delta.total_seconds() < 0:
                    delta = timedelta(seconds=0)
                if delta <= sla_threshold:
                    status = "green"
                    tooltip = f"Acknowledged within SLA ({self._format_duration(delta)})"
                else:
                    status = "red"
                    tooltip = f"Acknowledged after 1-hour SLA ({self._format_duration(delta)})"
            else:
                age = now - req.created_at
                if age.total_seconds() < 0:
                    age = timedelta(seconds=0)
                if age >= sla_threshold:
                    status = "red"
                    tooltip = f"No acknowledgement after {self._format_duration(age)}"
                elif age >= amber_threshold:
                    status = "amber"
                    tooltip = f"Awaiting acknowledgement ({self._format_duration(age)} elapsed)"
                else:
                    tooltip = f"Awaiting acknowledgement ({self._format_duration(age)} elapsed)"

            req.ack_sla_status = status
            req.ack_sla_tooltip = tooltip or "Acknowledgement status unavailable"

    def post(self, request, *args, **kwargs):
        if request.user.role != User.Roles.REQUESTOR:
            return redirect("hub:dashboard")
        form = RequestForm(request.POST, actor_role=User.Roles.REQUESTOR)
        if form.is_valid():
            req = form.save(commit=False)
            req.requestor = request.user
            full_name = request.user.get_full_name().strip()
            req.account_manager = full_name or request.user.username
            req._actor_user = request.user
            req._actor_source = "Dashboard · New Request"
            req.save()
            notify_engineer_assignment_email(
                req,
                actor_user=request.user,
                request=request,
            )
            self._notify_admins_new_request(req)
            messages.success(request, "Request submitted", extra_tags="request-success")
            return redirect("hub:dashboard")
        context = self.get_context_data(form=form)
        return self.render_to_response(context)

    @staticmethod
    def _notify_admins_new_request(request_obj):
        actor = request_obj.requestor.get_full_name() or request_obj.requestor.username
        priority_label = request_obj.get_priority_display()
        category_label = request_obj.get_product_category_display()
        due_display = request_obj.due_date.strftime("%b %d, %Y") if request_obj.due_date else "No due date"
        message = (
            f"New {priority_label} ticket {request_obj.reference_code} for {request_obj.account.name} "
            f"({category_label}) submitted by {actor}. Due {due_display}."
        )
        for admin in User.objects.filter(role=User.Roles.ADMIN):
            if admin.pk == request_obj.requestor_id:
                continue
            Notification.objects.create(
                recipient=admin,
                message=message,
                related_request=request_obj,
                actor=actor,
                source="Dashboard · New Request",
            )


class RequestDetailView(LoginRequiredMixin, DetailView):
    model = Request
    template_name = "hub/request_detail.html"
    context_object_name = "request_obj"

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.role == User.Roles.REQUESTOR:
            return qs.filter(requestor=user)
        if user.role == User.Roles.ENGINEER:
            return qs.filter(engineer=user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_obj = context["request_obj"]
        context["status_logs"] = request_obj.status_logs.select_related("author")
        can_comment = self._user_can_comment(self.request.user, request_obj)
        context["can_comment"] = can_comment
        if can_comment:
            context["log_form"] = kwargs.get("log_form") or StatusLogForm()
        if (
            self.request.user.role == User.Roles.ENGINEER
            and request_obj.engineer_id == self.request.user.id
        ):
            context["status_form"] = kwargs.get("status_form") or RequestStatusForm(instance=request_obj)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self._user_can_comment(request.user, self.object):
            return redirect("hub:request-detail", pk=self.object.pk)
        form = StatusLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.request = self.object
            log.author = request.user
            log.save()
            notify_status_update(log, "Request Detail · Status Update")
            messages.success(request, "Status log saved.")
            return redirect("hub:request-detail", pk=self.object.pk)
        context = self.get_context_data(log_form=form)
        return self.render_to_response(context)

    @staticmethod
    def _user_can_comment(user, request_obj):
        if not user.is_authenticated:
            return False
        if user.role == User.Roles.ADMIN:
            return True
        if user.role == User.Roles.ENGINEER and request_obj.engineer_id == user.id:
            return True
        if user.role == User.Roles.REQUESTOR and request_obj.requestor_id == user.id:
            return True
        return False

class RequestAdminUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Request
    form_class = RequestAdminForm
    template_name = "hub/request_admin_form.html"
    success_url = reverse_lazy("hub:dashboard")

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST.get("form_type") == "status_log":
            return self._handle_status_log_post(request)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance._actor_user = self.request.user
        form.instance._actor_source = "Admin · Manage Request"
        original = Request.objects.get(pk=form.instance.pk)
        previous_engineer_id = original.engineer_id
        previous_backup_id = original.backup_engineer_id
        changed_fields = list(form.changed_data)
        response = super().form_valid(form)
        if changed_fields:
            self._notify_request_update(original, self.object, changed_fields)
        notify_engineer_assignment_email(
            self.object,
            actor_user=self.request.user,
            request=self.request,
            previous_engineer_id=previous_engineer_id,
            previous_backup_id=previous_backup_id,
        )
        messages.success(self.request, "Request updated.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        referer = self.request.META.get("HTTP_REFERER")
        fallback = reverse("hub:dashboard")
        if not referer or referer == self.request.build_absolute_uri():
            context["back_url"] = fallback
        else:
            context["back_url"] = referer
        context["hide_sign_in_nav"] = True
        context["delete_url"] = reverse("hub:request-delete", args=[self.object.pk])
        context["status_logs"] = (
            StatusLog.objects.filter(request=self.object)
            .select_related("author")
            .order_by("-created_at")
        )
        context.setdefault("log_form", StatusLogForm())
        return context

    def _handle_status_log_post(self, request):
        form = StatusLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.request = self.object
            log.author = request.user
            log.save()
            notify_status_update(log, "Admin · Manage Request · Status Update")
            messages.success(request, "Status update posted.")
            return HttpResponseRedirect(self.request.path)
        if form.errors:
            message_field = form.fields.get("message")
            if message_field:
                existing_classes = message_field.widget.attrs.get("class", "")
                if "is-invalid" not in existing_classes.split():
                    message_field.widget.attrs["class"] = (existing_classes + " is-invalid").strip()
        context = self.get_context_data(log_form=form)
        return self.render_to_response(context)

    def _notify_request_update(self, original, updated, changed_fields):
        actor = self.request.user.get_full_name() or self.request.user.username
        summary_text = summarize_request_changes(original, updated, changed_fields)

        if not summary_text:
            return

        create_change_status_log(updated, self.request.user, "Admin · Manage Request", summary_text)
        recipients = {}
        if updated.requestor:
            recipients[updated.requestor.pk] = updated.requestor
        if updated.engineer:
            recipients[updated.engineer.pk] = updated.engineer
        if updated.backup_engineer:
            recipients[updated.backup_engineer.pk] = updated.backup_engineer

        recipients.pop(self.request.user.pk, None)

        for recipient in recipients.values():
            Notification.objects.create(
                recipient=recipient,
                message=f"{actor} updated {updated.reference_code}: {summary_text}",
                related_request=updated,
                actor=actor,
                source="Admin · Manage Request",
            )


class RequestUpdateView(LoginRequiredMixin, UpdateView):
    model = Request
    form_class = RequestForm
    template_name = "hub/request_update.html"
    success_url = reverse_lazy("hub:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.setdefault("actor_role", self.request.user.role)
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        if request.user.role != User.Roles.REQUESTOR:
            return redirect("hub:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(requestor=self.request.user)
            .select_related("account", "engineer")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["account_name_choices"] = context["form"].account_name_suggestions
        context["is_edit"] = True
        return context

    def form_valid(self, form):
        form.instance._actor_user = self.request.user
        form.instance._actor_source = "Requestor · Edit Request"
        original = Request.objects.get(pk=form.instance.pk)
        changed_fields = normalize_request_form_changed_fields(form.changed_data)
        response = super().form_valid(form)
        if original.account_id != self.object.account_id and "account" not in changed_fields:
            changed_fields.append("account")
        if changed_fields:
            notify_account_manager_request_update(
                self.request.user,
                original,
                self.object,
                changed_fields,
                "Requestor · Edit Request",
            )
        messages.success(self.request, "Request updated.")
        return response


class RequestCollaborativeManageView(LoginRequiredMixin, View):
    template_name = "hub/request_manager_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in {User.Roles.REQUESTOR, User.Roles.ENGINEER}:
            messages.error(request, "You are not allowed to manage this request.")
            return redirect("hub:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self):
        queryset = Request.objects.select_related("account", "engineer", "backup_engineer", "requestor")
        pk = self.kwargs["pk"]
        user = self.request.user

        if user.role == User.Roles.REQUESTOR:
            queryset = queryset.filter(pk=pk, requestor=user)
        elif user.role == User.Roles.ENGINEER:
            queryset = queryset.filter(pk=pk).filter(Q(engineer=user) | Q(backup_engineer=user))
        else:
            raise Http404

        return get_object_or_404(queryset)

    def get(self, request, *args, **kwargs):
        try:
            request_obj = self.get_object()
        except Http404:
            messages.error(request, "You are not allowed to manage this request.")
            return redirect("hub:dashboard")
        context = self.get_context_data(request_obj)
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        try:
            request_obj = self.get_object()
        except Http404:
            messages.error(request, "You are not allowed to manage this request.")
            return redirect("hub:dashboard")
        form_type = request.POST.get("form_type", "details")
        if form_type == "status_log":
            return self._handle_status_log_post(request, request_obj)
        if form_type == "status":
            return self._handle_status_update(request, request_obj)
        return self._handle_details_update(request, request_obj)

    def _actor_prefix(self) -> str:
        return "Requestor" if self.request.user.role == User.Roles.REQUESTOR else "Engineer"

    def _source_label(self, suffix: str) -> str:
        return f"{self._actor_prefix()} · {suffix}"

    def get_context_data(self, request_obj, form=None, status_form=None, log_form=None):
        if form is None:
            form = RequestForm(instance=request_obj, actor_role=self.request.user.role)
        status_allowed = self.request.user.role == User.Roles.ENGINEER
        if status_allowed and status_form is None:
            status_form = RequestStatusForm(instance=request_obj)
        elif not status_allowed:
            status_form = None
        if log_form is None:
            log_form = StatusLogForm()

        referer = self.request.META.get("HTTP_REFERER")
        fallback = reverse("hub:dashboard")
        if not referer or referer == self.request.build_absolute_uri():
            back_url = fallback
        else:
            back_url = referer

        return {
            "object": request_obj,
            "form": form,
            "status_form": status_form,
            "log_form": log_form,
            "status_logs": request_obj.status_logs.select_related("author").order_by("-created_at"),
            "account_name_choices": getattr(form, "account_name_suggestions", ()),
            "back_url": back_url,
            "status_allowed": status_allowed,
        }

    def _handle_details_update(self, request, request_obj):
        form = RequestForm(request.POST, instance=request_obj, actor_role=request.user.role)
        if form.is_valid():
            source_label = self._source_label("Manage Request")
            form.instance._actor_user = request.user
            form.instance._actor_source = source_label
            original = Request.objects.get(pk=request_obj.pk)
            changed_fields = normalize_request_form_changed_fields(form.changed_data)
            form.save()
            if original.account_id != request_obj.account_id and "account" not in changed_fields:
                changed_fields.append("account")
            if changed_fields:
                notify_account_manager_request_update(
                    request.user,
                    original,
                    request_obj,
                    changed_fields,
                    source_label,
                )
            messages.success(request, "Request details updated.")
            return HttpResponseRedirect(request.path)
        context = self.get_context_data(request_obj, form=form)
        return render(request, self.template_name, context)

    def _handle_status_update(self, request, request_obj):
        if request.user.role != User.Roles.ENGINEER:
            messages.error(request, "Only the assigned engineer can update the status.")
            return HttpResponseRedirect(request.path)
        status_form = RequestStatusForm(request.POST, instance=request_obj)
        if status_form.is_valid():
            source_label = self._source_label("Manage Request · Status")
            original = Request.objects.get(pk=request_obj.pk)
            request_obj._actor_user = request.user
            request_obj._actor_source = source_label
            status_form.save()
            changed_fields = []
            if original.status != request_obj.status:
                changed_fields.append("status")
            if original.end_date != request_obj.end_date:
                changed_fields.append("end_date")
            if changed_fields:
                notify_account_manager_request_update(
                    request.user,
                    original,
                    request_obj,
                    changed_fields,
                    source_label,
                )
            messages.success(request, "Request status updated.")
            return HttpResponseRedirect(request.path)
        if status_form.errors:
            for field in status_form:
                if field.errors:
                    existing_classes = field.field.widget.attrs.get("class", "")
                    if "is-invalid" not in existing_classes.split():
                        field.field.widget.attrs["class"] = (existing_classes + " is-invalid").strip()
        context = self.get_context_data(request_obj, status_form=status_form)
        return render(request, self.template_name, context)

    def _handle_status_log_post(self, request, request_obj):
        log_form = StatusLogForm(request.POST)
        if log_form.is_valid():
            log = log_form.save(commit=False)
            log.request = request_obj
            log.author = request.user
            log.save()
            source_label = self._source_label("Manage Request · Status Update")
            notify_status_update(log, source_label)
            messages.success(request, "Status update posted.")
            return HttpResponseRedirect(request.path)
        if log_form.errors:
            message_field = log_form.fields.get("message")
            if message_field:
                existing_classes = message_field.widget.attrs.get("class", "")
                if "is-invalid" not in existing_classes.split():
                    message_field.widget.attrs["class"] = (existing_classes + " is-invalid").strip()
        context = self.get_context_data(request_obj, log_form=log_form)
        return render(request, self.template_name, context)


class RequestStatusUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        request_obj = get_object_or_404(
            Request.objects.select_related("engineer", "requestor"),
            pk=pk,
        )

        if request.user.role != User.Roles.ENGINEER or request_obj.engineer_id != request.user.id:
            messages.error(request, "You are not allowed to update this request's status.")
            return redirect("hub:request-detail", pk=pk)

        original = Request.objects.get(pk=request_obj.pk)
        form = RequestStatusForm(request.POST, instance=request_obj)
        if form.is_valid():
            request_obj._actor_user = request.user
            request_obj._actor_source = "Engineer · Status Update"
            form.save()
            changed_fields = []
            if original.status != request_obj.status:
                changed_fields.append("status")
            if original.end_date != request_obj.end_date:
                changed_fields.append("end_date")
            if changed_fields:
                summary_text = summarize_request_changes(original, request_obj, changed_fields)
                create_change_status_log(request_obj, request.user, "Engineer · Status Update", summary_text)
            messages.success(request, "Request status updated.")
        else:
            messages.error(request, "Unable to update status. Please try again.")
        return redirect("hub:request-detail", pk=pk)


class RequestNudgeView(AdminRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        request_obj = get_object_or_404(Request.objects.select_related("engineer", "requestor"), pk=pk)
        target = request.POST.get("target")

        if target not in {"engineer", "account_manager"}:
            messages.error(request, "Choose who should receive the follow-up notification.")
            return redirect("hub:dashboard")

        if target == "engineer":
            if not request_obj.engineer:
                messages.error(request, "This request does not have an assigned engineer yet.")
                return redirect("hub:dashboard")
            recipient = request_obj.engineer
            target_label = "Engineer"
        else:
            recipient = request_obj.requestor
            target_label = "Requestor"

        sender_name = request.user.get_full_name() or request.user.username
        Notification.objects.create(
            recipient=recipient,
            message=f"{sender_name} requested an update on {request_obj.reference_code}.",
            related_request=request_obj,
            actor=sender_name,
            source="Admin · Nudge",
        )
        messages.success(request, f"{target_label} notified for {request_obj.reference_code}.")
        return redirect("hub:dashboard")


class RequestDeleteView(LoginRequiredMixin, DeleteView):
    model = Request
    success_url = reverse_lazy("hub:dashboard")
    template_name = "hub/request_confirm_delete.html"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.role == User.Roles.ADMIN:
            return qs
        if user.role == User.Roles.REQUESTOR:
            return qs.filter(requestor=user)
        return qs.none()

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, "Request deleted successfully.")
        return response


class RequestTeamsRedirectView(AdminOrEngineerRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        request_obj = get_object_or_404(Request.objects.select_related("engineer", "requestor"), pk=pk)
        teams_url = request_obj.teams_chat_url

        if not teams_url:
            messages.error(
                request,
                "Unable to start a Teams chat. Ensure the engineer and requestor both have emails configured.",
            )
            return redirect("hub:dashboard")

        messages.info(request, "Opening Microsoft Teams in a new tab…")
        return redirect(teams_url)


class RequestOutlookRedirectView(AdminOrEngineerRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        request_obj = get_object_or_404(
            Request.objects.select_related("engineer", "backup_engineer", "requestor", "account"),
            pk=pk,
        )

        redirect_target = request.META.get("HTTP_REFERER") or reverse("hub:dashboard")

        if request.user.role == User.Roles.ENGINEER:
            if request.user != request_obj.engineer and request.user != request_obj.backup_engineer:
                messages.error(request, "You are not allowed to draft emails for this request.")
                return redirect(redirect_target)
            already_launched = RequestCommunication.objects.filter(
                request=request_obj,
                user=request.user,
                channel=RequestCommunication.Channel.OUTLOOK,
            ).exists()
            if already_launched:
                messages.warning(request, "You already launched the Outlook draft for this request.")
                return redirect(redirect_target)

        engineer_email = (
            request_obj.engineer.email if request_obj.engineer and request_obj.engineer.email else None
        )
        manager_email = (
            request_obj.requestor.email if request_obj.requestor and request_obj.requestor.email else None
        )
        backup_email = (
            request_obj.backup_engineer.email
            if request_obj.backup_engineer and request_obj.backup_engineer.email
            else None
        )

        if not engineer_email or not manager_email:
            messages.error(
                request,
                "Unable to draft an email. Ensure the engineer and requestor both have emails configured.",
            )
            return redirect(redirect_target)

        to_addresses = {engineer_email, manager_email}
        cc_addresses = {"ESGRequestHub@phildata.com"}
        if backup_email:
            cc_addresses.add(backup_email)

        recipients = ",".join(sorted(to_addresses))
        cc_field = ",".join(sorted(cc_addresses))
        subject = quote(f"{request_obj.reference_code} · {request_obj.account.name}")

        requestor = request_obj.requestor
        if requestor:
            requestor_name = requestor.get_full_name() or requestor.username
        else:
            requestor_name = request_obj.account_manager or "Requestor"

        engagement_display = request_obj.get_engagement_type_display()
        product_display = request_obj.get_product_category_display()

        description_clean = (request_obj.description or "").strip()
        if description_clean:
            description_line = description_clean.replace("\r", " ").replace("\n", " ")
        else:
            description_line = "No description provided."

        sender_name = request.user.get_full_name() or request.user.username

        body_template = (
            "Hello {requestor_name},\n\n"
            "This is to acknowledge your request in Request Hub. We've logged the details below and started processing it:\n\n"
            "Reference: {reference}\n"
            "Request Type: {request_type}\n"
            "Product: {product}\n"
            "Description: {description}\n\n"
            "I will reach out with updates or any follow-up questions.\n"
            "If you have additional information or questions, simply reply to this email and we'll continue the thread.\n\n"                      
        )

        body = quote(
            body_template.format(
                requestor_name=requestor_name,
                reference=request_obj.reference_code,
                request_type=engagement_display,
                product=product_display,
                description=description_line,
                sender_name=sender_name,
            )
        )

        RequestCommunication.objects.create(
            request=request_obj,
            user=request.user,
            channel=RequestCommunication.Channel.OUTLOOK,
        )

        mailto_parts = [f"mailto:{recipients}", f"subject={subject}", f"body={body}"]
        if cc_field:
            mailto_parts.insert(1, f"cc={quote(cc_field)}")

        outlook_url = "?".join([mailto_parts[0], "&".join(mailto_parts[1:])])
        messages.info(request, "Drafting email in your default mail client…")
        return render(
            request,
            "hub/outlook_redirect.html",
            {"mailto_url": outlook_url},
        )


class RequestTeamsRedirectView(AdminOrEngineerRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        request_obj = get_object_or_404(
            Request.objects.select_related("engineer", "backup_engineer", "requestor", "account"),
            pk=pk,
        )

        redirect_target = request.META.get("HTTP_REFERER") or reverse("hub:dashboard")

        if request.user.role == User.Roles.ENGINEER:
            if request.user != request_obj.engineer and request.user != request_obj.backup_engineer:
                messages.error(request, "You are not allowed to start a Teams chat for this request.")
                return redirect(redirect_target)
            already_launched = RequestCommunication.objects.filter(
                request=request_obj,
                user=request.user,
                channel=RequestCommunication.Channel.TEAMS,
            ).exists()
            if already_launched:
                messages.warning(request, "You already launched the Teams chat for this request.")
                return redirect(redirect_target)

        teams_url = request_obj.teams_chat_url
        if not teams_url:
            messages.error(
                request,
                "Unable to start a Teams chat. Ensure the engineer and requestor have email addresses configured.",
            )
            return redirect(redirect_target)

        RequestCommunication.objects.create(
            request=request_obj,
            user=request.user,
            channel=RequestCommunication.Channel.TEAMS,
        )

        messages.info(request, "Launching Microsoft Teams…")
        return render(
            request,
            "hub/teams_redirect.html",
            {"teams_url": teams_url},
        )


class RequestExportCSVView(AdminRequiredMixin, LoginRequiredMixin, View):
    """Allow administrators to export all requests to a CSV download."""

    columns = (
        "Reference",
        "Account",
        "Requestor",
        "Requestor Email",
        "Engineer",
        "Engineer Email",
        "Priority",
        "Status",
        "Engagement",
        "Start Date",
        "Due Date",
        "End Date",
        "Description",
        "Created",
        "Updated",
    )

    def get(self, request, *args, **kwargs):
        timestamp = timezone.now().strftime("%Y%m%d-%H%M%S")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="requests-{timestamp}.csv"'

        writer = csv.writer(response)
        writer.writerow(self.columns)

        queryset = Request.objects.select_related("account", "requestor", "engineer").order_by("reference_code")
        for req in queryset:
            requestor = req.requestor
            engineer = req.engineer
            writer.writerow(
                [
                    req.reference_code,
                    req.account.name if req.account else "",
                    requestor.get_full_name() or requestor.username if requestor else "",
                    requestor.email if requestor else "",
                    engineer.get_full_name() or engineer.username if engineer else "",
                    engineer.email if engineer else "",
                    req.get_priority_display(),
                    req.get_status_display(),
                    req.get_engagement_type_display(),
                    req.start_date.strftime("%Y-%m-%d") if req.start_date else "",
                    req.due_date.strftime("%Y-%m-%d") if req.due_date else "",
                    req.end_date.strftime("%Y-%m-%d") if req.end_date else "",
                    (req.description or "").replace("\r\n", " ").replace("\n", " "),
                    req.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    req.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        return response


class RequestReportView(AdminRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = "hub/report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_view = (self.request.GET.get("report_view") or "operational").lower()
        if report_view not in {"operational", "activity"}:
            report_view = "operational"
        context["report_view"] = report_view

        if report_view == "activity":
            context.update(self._build_activity_log_context())
        else:
            context.update(self._build_operational_context())
        return context

    def _build_operational_context(self):
        total_requests = Request.objects.count()
        account_manager_qs = (
            Request.objects.values("account_manager")
            .annotate(
                total=Count("id"),
                ongoing=Count("id", filter=Q(status=Request.Status.ONGOING)),
                completed=Count("id", filter=Q(status=Request.Status.COMPLETED)),
            )
            .order_by("-total", "account_manager")
        )
        account_manager_data = []
        for item in account_manager_qs:
            label = item["account_manager"] or "Unspecified"
            account_manager_data.append(
                {
                    "name": label,
                    "total": item["total"],
                    "ongoing": item["ongoing"],
                    "completed": item["completed"],
                }
            )

        engineer_qs = (
            Request.objects.values(
                "engineer",
                "engineer__first_name",
                "engineer__last_name",
                "engineer__username",
            )
            .annotate(
                total=Count("id"),
                ongoing=Count("id", filter=Q(status=Request.Status.ONGOING)),
                completed=Count("id", filter=Q(status=Request.Status.COMPLETED)),
            )
            .order_by("-total", "engineer__username")
        )
        engineer_data = []
        for item in engineer_qs:
            if item["engineer"] is None:
                name = "Unassigned"
            else:
                first = item.get("engineer__first_name") or ""
                last = item.get("engineer__last_name") or ""
                full_name = f"{first} {last}".strip()
                name = full_name or item.get("engineer__username") or "Engineer"
            engineer_data.append(
                {
                    "name": name,
                    "total": item["total"],
                    "ongoing": item["ongoing"],
                    "completed": item["completed"],
                }
            )

        status_labels = dict(Request.Status.choices)
        status_counts = {status: 0 for status, _ in Request.Status.choices}
        for item in Request.objects.values("status").annotate(total=Count("id")):
            status_counts[item["status"]] = item["total"]
        status_breakdown = [
            {
                "label": status_labels.get(status, status.title()),
                "total": total,
            }
            for status, total in status_counts.items()
            if total > 0
        ]

        engagement_counts = {
            value: {"total": 0, "ongoing": 0, "completed": 0}
            for value, _ in Request.Engagement.choices
        }
        for item in Request.objects.values("engagement_type", "status").annotate(total=Count("id")):
            key = item["engagement_type"]
            bucket = engagement_counts.setdefault(
                key,
                {"total": 0, "ongoing": 0, "completed": 0},
            )
            bucket["total"] += item["total"]
            if item["status"] == Request.Status.ONGOING:
                bucket["ongoing"] += item["total"]
            elif item["status"] == Request.Status.COMPLETED:
                bucket["completed"] += item["total"]

        engagement_labels_map = dict(Request.Engagement.choices)
        engagement_order = [
            Request.Engagement.OPPORTUNITY,
            Request.Engagement.SUPPORT,
            Request.Engagement.TRAINING,
            Request.Engagement.INQUIRY,
        ]

        product_categories = ["Azure", "M365", "Others"]
        product_buckets = {
            category: {"total": 0, "ongoing": 0, "completed": 0}
            for category in product_categories
        }
        for item in Request.objects.values("product_category", "status").annotate(total=Count("id")):
            category = item["product_category"] or "Others"
            normalized = (category or "").lower()
            if normalized == "azure" or category == "Azure":
                key = "Azure"
            elif normalized in {"m365", "microsoft 365"}:
                key = "M365"
            else:
                key = "Others"

            bucket = product_buckets.setdefault(key, {"total": 0, "ongoing": 0, "completed": 0})
            bucket["total"] += item["total"]
            if item["status"] == Request.Status.ONGOING:
                bucket["ongoing"] += item["total"]
            elif item["status"] == Request.Status.COMPLETED:
                bucket["completed"] += item["total"]

        engagement_chart_payload = {
            "labels": [engagement_labels_map.get(value, value.title()) for value in engagement_order],
            "totals": [engagement_counts.get(value, {"total": 0})["total"] for value in engagement_order],
            "ongoing": [engagement_counts.get(value, {"ongoing": 0})["ongoing"] for value in engagement_order],
            "completed": [engagement_counts.get(value, {"completed": 0})["completed"] for value in engagement_order],
        }
        product_chart_payload = {
            "labels": list(product_buckets.keys()),
            "totals": [bucket["total"] for bucket in product_buckets.values()],
            "ongoing": [bucket["ongoing"] for bucket in product_buckets.values()],
            "completed": [bucket["completed"] for bucket in product_buckets.values()],
        }
        engagement_chart_has_data = any(value > 0 for value in engagement_chart_payload["totals"])
        product_chart_has_data = any(value > 0 for value in product_chart_payload["totals"])

        return {
            "totals": {
                "requests": total_requests,
                "account_managers": (
                    Request.objects.exclude(account_manager__isnull=True)
                    .exclude(account_manager__exact="")
                    .values("account_manager")
                    .distinct()
                    .count()
                ),
                "engineers": (
                    Request.objects.exclude(engineer__isnull=True)
                    .values("engineer")
                    .distinct()
                    .count()
                ),
                "ongoing": Request.objects.filter(status=Request.Status.ONGOING).count(),
                "completed": Request.objects.filter(status=Request.Status.COMPLETED).count(),
            },
            "account_manager_chart": {
                "labels": [item["name"] for item in account_manager_data],
                "totals": [item["total"] for item in account_manager_data],
                "ongoing": [item["ongoing"] for item in account_manager_data],
                "completed": [item["completed"] for item in account_manager_data],
            },
            "engineer_chart": {
                "labels": [item["name"] for item in engineer_data],
                "totals": [item["total"] for item in engineer_data],
                "ongoing": [item["ongoing"] for item in engineer_data],
                "completed": [item["completed"] for item in engineer_data],
            },
            "engagement_chart": engagement_chart_payload,
            "engagement_chart_has_data": engagement_chart_has_data,
            "product_chart": product_chart_payload,
            "product_chart_has_data": product_chart_has_data,
            "account_manager_stats": account_manager_data,
            "engineer_stats": engineer_data,
            "status_breakdown": status_breakdown,
        }

    def _build_activity_log_context(self):
        logs_qs = EngineerActivityLog.objects.select_related("engineer", "account", "request")

        total_hours = logs_qs.aggregate(total=Sum("actual_hours")) or {}
        billable_hours = logs_qs.filter(is_billable=True).aggregate(total=Sum("actual_hours")) or {}
        non_billable_hours = logs_qs.filter(is_billable=False).aggregate(total=Sum("actual_hours")) or {}

        total_hours_value = total_hours.get("total") or Decimal("0")
        billable_hours_value = billable_hours.get("total") or Decimal("0")
        non_billable_hours_value = non_billable_hours.get("total") or Decimal("0")

        engineer_hours = (
            logs_qs.values(
                "engineer",
                "engineer__first_name",
                "engineer__last_name",
                "engineer__username",
            )
            .annotate(
                total_hours=Sum("actual_hours"),
                billable_hours=Sum("actual_hours", filter=Q(is_billable=True)),
            )
            .order_by("engineer__first_name", "engineer__last_name", "engineer__username")
        )

        engineer_chart = {
            "labels": [],
            "billable": [],
            "non_billable": [],
        }
        engineer_table = []
        for row in engineer_hours:
            if row["engineer"] is None:
                display_name = "Unassigned"
            else:
                first = (row.get("engineer__first_name") or "").strip()
                last = (row.get("engineer__last_name") or "").strip()
                full_name = f"{first} {last}".strip()
                display_name = full_name or row.get("engineer__username") or "Engineer"
            total_val = row.get("total_hours") or Decimal("0")
            billable_val = row.get("billable_hours") or Decimal("0")
            non_billable_val = total_val - billable_val
            engineer_chart["labels"].append(display_name)
            engineer_chart["billable"].append(float(billable_val))
            engineer_chart["non_billable"].append(float(non_billable_val))
            engineer_table.append(
                {
                    "name": display_name,
                    "total_hours": total_val,
                    "billable_hours": billable_val,
                    "non_billable_hours": non_billable_val,
                }
            )

        activity_label_map = dict(EngineerActivityLog.ActivityType.choices)
        activity_hours = (
            logs_qs.values("activity_type")
            .annotate(
                total_hours=Sum("actual_hours"),
                billable_hours=Sum("actual_hours", filter=Q(is_billable=True)),
            )
            .order_by("activity_type")
        )

        activity_chart = {
            "labels": [],
            "billable": [],
            "non_billable": [],
        }
        activity_table = []
        for row in activity_hours:
            activity_key = row.get("activity_type")
            label = activity_label_map.get(activity_key, "Unspecified")
            total_val = row.get("total_hours") or Decimal("0")
            billable_val = row.get("billable_hours") or Decimal("0")
            non_billable_val = total_val - billable_val
            activity_chart["labels"].append(label)
            activity_chart["billable"].append(float(billable_val))
            activity_chart["non_billable"].append(float(non_billable_val))
            activity_table.append(
                {
                    "label": label,
                    "total_hours": total_val,
                    "billable_hours": billable_val,
                    "non_billable_hours": non_billable_val,
                }
            )

        location_label_map = dict(EngineerActivityLog.Location.choices)
        location_hours = (
            logs_qs.values("location")
            .annotate(total_hours=Sum("actual_hours"))
            .order_by("location")
        )
        location_chart = {
            "labels": [],
            "totals": [],
        }
        for row in location_hours:
            location_key = row.get("location")
            label = location_label_map.get(location_key, "Unspecified")
            total_val = row.get("total_hours") or Decimal("0")
            location_chart["labels"].append(label)
            location_chart["totals"].append(float(total_val))

        billable_chart = {
            "labels": ["Billable", "Not Billable"],
            "totals": [
                float(billable_hours_value),
                float(non_billable_hours_value),
            ],
        }

        recent_logs = list(
            logs_qs.order_by("-request_date", "-created_at")[:50]
        )

        return {
            "activity_totals": {
                "entries": logs_qs.count(),
                "total_hours": total_hours_value,
                "billable_hours": billable_hours_value,
                "non_billable_hours": non_billable_hours_value,
                "unique_accounts": logs_qs.values("account").distinct().count(),
            },
            "activity_engineer_chart": engineer_chart,
            "activity_engineer_table": engineer_table,
            "activity_type_chart": activity_chart,
            "activity_type_table": activity_table,
            "activity_location_chart": location_chart,
            "activity_billable_chart": billable_chart,
            "activity_logs": recent_logs,
        }


class UserManagementView(AdminRequiredMixin, LoginRequiredMixin, View):
    template_name = "hub/management.html"
    formset_class = modelformset_factory(User, form=UserManagementForm, extra=1, can_delete=True)
    account_form_class = modelformset_factory(Account, form=AccountManagementForm, extra=1, can_delete=True)

    def get_queryset(self):
        return User.objects.order_by("date_joined", "username")

    def get(self, request, *args, **kwargs):
        self._sync_account_baseline()
        formset = self.formset_class(queryset=self.get_queryset())
        account_formset = self.account_form_class(queryset=Account.objects.order_by("name"))
        self._prepare_formset(formset)
        self._prepare_account_formset(account_formset)
        return render(request, self.template_name, self._build_context(formset, account_formset))

    def post(self, request, *args, **kwargs):
        active_tab = request.POST.get("active_tab", "users")
        self._sync_account_baseline()
        if active_tab != "accounts":
            user_action_value = request.POST.get("user_action")
            if user_action_value:
                action_response = self._handle_user_action_request(request, user_action_value)
                if action_response:
                    return action_response
        formset = self.formset_class(request.POST, queryset=self.get_queryset())
        account_formset = self.account_form_class(request.POST, queryset=Account.objects.order_by("name"))
        self._prepare_formset(formset)
        self._prepare_account_formset(account_formset)

        if active_tab == "accounts":
            return self._handle_account_submission(request, account_formset, formset)

        if formset.is_valid():
            current_admins = User.objects.filter(role=User.Roles.ADMIN).count()
            admin_delta = 0
            pending_error = False
            admin_removal_candidates = []

            for form in formset:
                if not form.cleaned_data:
                    continue

                is_delete = form.cleaned_data.get("DELETE")
                if is_delete:
                    if form.instance.pk and form.instance.is_superuser:
                        form.add_error("DELETE", "Superuser accounts cannot be deleted.")
                        pending_error = True
                        continue
                    if form.instance.pk and form.instance.role == User.Roles.ADMIN:
                        admin_delta -= 1
                        admin_removal_candidates.append((form, "delete"))
                    continue

                if not form.instance.pk and not form.has_changed():
                    continue

                new_role = form.cleaned_data.get("role")
                original_role = form.instance.role if form.instance.pk else None

                if form.instance.pk and form.instance.is_superuser and new_role != User.Roles.ADMIN:
                    form.add_error("role", "Superuser accounts must remain administrators.")
                    pending_error = True

                if form.instance.pk:
                    if original_role == User.Roles.ADMIN and new_role != User.Roles.ADMIN:
                        admin_delta -= 1
                        admin_removal_candidates.append((form, "role"))
                    elif original_role != User.Roles.ADMIN and new_role == User.Roles.ADMIN:
                        admin_delta += 1
                else:
                    if new_role == User.Roles.ADMIN:
                        admin_delta += 1

            if pending_error:
                return render(request, self.template_name, self._build_context(formset, account_formset))

            if current_admins + admin_delta <= 0:
                if admin_removal_candidates:
                    form, field = admin_removal_candidates[0]
                    if field == "delete":
                        form.add_error("DELETE", "At least one administrator must remain.")
                    else:
                        form.add_error("role", "At least one administrator must remain.")
                else:
                    messages.error(request, "At least one administrator must remain.")
                return render(request, self.template_name, self._build_context(formset, account_formset))

            created_count = 0
            updated_count = 0
            deleted_count = 0

            with transaction.atomic():
                for form in formset:
                    if not form.cleaned_data:
                        continue

                    if form.cleaned_data.get("DELETE"):
                        if form.instance.pk:
                            form.instance.delete()
                            deleted_count += 1
                        continue

                    if not form.has_changed() and form.instance.pk:
                        continue

                    is_new = not form.instance.pk
                    form.save()
                    if is_new:
                        created_count += 1
                    else:
                        updated_count += 1

            if created_count or updated_count or deleted_count:
                parts = []
                if created_count:
                    parts.append(f"created {created_count} user account{'s' if created_count != 1 else ''}")
                if updated_count:
                    parts.append(f"updated {updated_count} user account{'s' if updated_count != 1 else ''}")
                if deleted_count:
                    parts.append(f"removed {deleted_count} user account{'s' if deleted_count != 1 else ''}")
                messages.success(request, ", ".join(parts).capitalize() + ".")
            else:
                messages.info(request, "No changes detected.")
            return redirect("hub:management")

        return render(request, self.template_name, self._build_context(formset, account_formset))

    def _handle_account_submission(self, request, account_formset, user_formset):
        if account_formset.is_valid():
            created = updated = deleted = 0
            with transaction.atomic():
                for form in account_formset:
                    if not form.cleaned_data:
                        continue
                    if form.cleaned_data.get("DELETE"):
                        if form.instance.pk:
                            form.instance.delete()
                            deleted += 1
                        continue
                    if not form.instance.pk and not form.has_changed():
                        continue
                    is_new = not form.instance.pk
                    form.save()
                    if is_new:
                        created += 1
                    else:
                        updated += 1
            if created or updated or deleted:
                parts = []
                if created:
                    parts.append(f"created {created} account{'s' if created != 1 else ''}")
                if updated:
                    parts.append(f"updated {updated} account{'s' if updated != 1 else ''}")
                if deleted:
                    parts.append(f"removed {deleted} account{'s' if deleted != 1 else ''}")
                messages.success(request, ", ".join(parts).capitalize() + ".")
            else:
                messages.info(request, "No account changes detected.")
            return redirect("hub:management")
        return render(request, self.template_name, self._build_context(user_formset, account_formset, active_tab="accounts"))

    def _build_context(self, formset, account_formset, active_tab="users"):
        return {
            "formset": formset,
            "account_formset": account_formset,
            "total_users": User.objects.count(),
            "total_accounts": Account.objects.count(),
            "active_tab": active_tab,
            "default_password": getattr(settings, "DEFAULT_USER_PASSWORD", "@Password"),
        }

    @staticmethod
    def _prepare_formset(formset):
        for form in formset:
            delete_field = form.fields.get("DELETE")
            if delete_field:
                existing_class = delete_field.widget.attrs.get("class", "")
                delete_field.widget.attrs["class"] = (existing_class + " form-check-input").strip()

    @staticmethod
    def _prepare_account_formset(formset):
        for form in formset:
            delete_field = form.fields.get("DELETE")
            if delete_field:
                existing_class = delete_field.widget.attrs.get("class", "")
                delete_field.widget.attrs["class"] = (existing_class + " form-check-input").strip()

    @staticmethod
    def _sync_account_baseline():
        if Account.objects.exists():
            return

        seed_accounts = []
        for raw_name in ACCOUNT_NAME_RAW:
            normalized = (raw_name or "").strip()
            if not normalized:
                continue
            seed_accounts.append(Account(name=normalized))

        if seed_accounts:
            Account.objects.bulk_create(seed_accounts, ignore_conflicts=True)

    def _handle_user_action_request(self, request, action_value):
        action, separator, raw_user_id = (action_value or "").partition(":")
        if not separator:
            messages.error(request, "We could not determine the requested action.")
            return redirect("hub:management")

        try:
            target_user = User.objects.get(pk=int(raw_user_id))
        except (User.DoesNotExist, ValueError):
            messages.error(request, "We could not find the selected user account.")
            return redirect("hub:management")

        if action == "reset_password":
            return self._reset_user_password(request, target_user)

        messages.error(request, "Unknown action requested.")
        return redirect("hub:management")

    @staticmethod
    def _clear_user_sessions(target_user: User) -> int:
        removed = 0
        user_id = str(target_user.pk)
        session_qs = Session.objects.filter(expire_date__gte=timezone.now())
        for session in session_qs:
            try:
                data = session.get_decoded()
            except Exception:
                continue
            if str(data.get("_auth_user_id")) == user_id:
                session.delete()
                removed += 1
        return removed

    def _reset_user_password(self, request, target_user: User):
        default_password = getattr(settings, "DEFAULT_USER_PASSWORD", "@Password")
        target_user.set_password(default_password)
        target_user.must_change_password = True
        target_user.save(update_fields=["password", "must_change_password"])
        removed_sessions = self._clear_user_sessions(target_user)
        display_name = target_user.get_full_name() or target_user.username
        message = (
            f"Reset password for {display_name}. The default password has been restored and they must set a new password on next sign-in."
        )
        if removed_sessions:
            message += f" Ended {removed_sessions} session{'s' if removed_sessions != 1 else ''}."
        messages.success(request, message)
        return redirect("hub:management")


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "hub/notifications.html"
    context_object_name = "notifications"

    def get_queryset(self):
        queryset = (
            self.request.user.notifications.select_related("related_request")
            .order_by("-created_at")
        )
        user = self.request.user
        if getattr(user, "role", None) == User.Roles.ADMIN:
            queryset = queryset.filter(source__icontains="new request")
        return queryset


class NotificationReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.mark_read()
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("hub:notifications")))


class NotificationFollowRedirectView(LoginRequiredMixin, View):
    def get(self, request, pk):
        notification = get_object_or_404(
            Notification.objects.select_related("related_request"),
            pk=pk,
            recipient=request.user,
        )
        notification.mark_read()
        if notification.related_request:
            return redirect("hub:request-detail", pk=notification.related_request.pk)
        return redirect("hub:notifications")


class NotificationDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.delete()
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("hub:notifications")))
