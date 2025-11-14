import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, DeleteView, ListView, TemplateView, UpdateView
from urllib.parse import quote

from accounts.models import User

from .forms import RequestAdminForm, RequestForm, StatusLogForm
from .constants import ACCOUNT_NAME_SUGGESTIONS
from .models import Notification, Request
from .mixins import AdminRequiredMixin


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "hub/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["role"] = user.role
        context["notifications"] = user.notifications.filter(is_read=False)[:10]

        if user.role == User.Roles.REQUESTOR:
            context["requests"] = Request.objects.filter(requestor=user).select_related("account", "engineer")
            context["form"] = kwargs.get("form") or RequestForm()
            context["account_name_choices"] = ACCOUNT_NAME_SUGGESTIONS
        elif user.role == User.Roles.ENGINEER:
            context["requests"] = (
                Request.objects.filter(engineer=user)
                .select_related("account", "requestor")
                .order_by("status", "due_date")
            )
        else:
            context["requests"] = (
                Request.objects.select_related("account", "engineer", "requestor")
                .order_by("status", "due_date")
            )
            context["overdue_count"] = Request.objects.filter(
                status=Request.Status.ONGOING,
                due_date__lt=timezone.now().date(),
            ).count()
        return context

    def post(self, request, *args, **kwargs):
        if request.user.role != User.Roles.REQUESTOR:
            return redirect("hub:dashboard")
        form = RequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.requestor = request.user
            full_name = request.user.get_full_name().strip()
            req.account_manager = full_name or request.user.username
            req.save()
            messages.success(request, "Request submitted successfully.")
            return redirect("hub:dashboard")
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


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

    def form_valid(self, form):
        messages.success(self.request, "Request updated.")
        return super().form_valid(form)


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
            target_label = "Account Manager"

        sender_name = request.user.get_full_name() or request.user.username
        Notification.objects.create(
            recipient=recipient,
            message=f"{sender_name} requested an update on {request_obj.reference_code}.",
            related_request=request_obj,
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


class RequestTeamsRedirectView(AdminRequiredMixin, LoginRequiredMixin, View):
    def post(self, request, pk):
        request_obj = get_object_or_404(Request.objects.select_related("engineer", "requestor"), pk=pk)

        engineer_email = (
            request_obj.engineer.email if request_obj.engineer and request_obj.engineer.email else None
        )
        manager_email = (
            request_obj.requestor.email if request_obj.requestor and request_obj.requestor.email else None
        )

        if not engineer_email or not manager_email:
            messages.error(
                request,
                "Unable to start a Teams chat. Ensure the engineer and account manager both have emails configured.",
            )
            return redirect("hub:dashboard")

        participants = [engineer_email, manager_email]
        users_param = quote(",".join(participants))
        group_name = f"{request_obj.reference_code} · {request_obj.account.name}"
        topic_param = quote(group_name)
        teams_url = (
            "https://teams.microsoft.com/l/chat/0/0?users="
            f"{users_param}&topicName={topic_param}"
        )

        messages.info(request, "Opening Microsoft Teams in a new tab…")
        return redirect(teams_url)


class RequestOutlookRedirectView(AdminRequiredMixin, LoginRequiredMixin, View):
    FIELD_TEMPLATE = (
        "Reference: {reference}\n"
        "Account: {account}\n"
        "Account Manager: {manager}\n"
        "Engineer: {engineer}\n"
        "Priority: {priority}\n"
        "Status: {status}\n"
        "Due Date: {due_date}\n"
        "Engagement Type: {engagement}\n"
        "Description: {description}"
    )

    def post(self, request, pk):
        request_obj = get_object_or_404(Request.objects.select_related("engineer", "requestor", "account"), pk=pk)

        engineer_email = (
            request_obj.engineer.email if request_obj.engineer and request_obj.engineer.email else None
        )
        manager_email = (
            request_obj.requestor.email if request_obj.requestor and request_obj.requestor.email else None
        )

        if not engineer_email or not manager_email:
            messages.error(
                request,
                "Unable to draft an email. Ensure the engineer and account manager both have emails configured.",
            )
            return redirect("hub:dashboard")

        recipients = ",".join({engineer_email, manager_email})
        subject = quote(f"{request_obj.reference_code} · {request_obj.account.name}")

        body_content = self.FIELD_TEMPLATE.format(
            reference=request_obj.reference_code,
            account=request_obj.account.name,
            manager=request_obj.account_manager,
            engineer=request_obj.engineer.get_full_name() if request_obj.engineer else "Unassigned",
            priority=request_obj.get_priority_display(),
            status=request_obj.get_status_display(),
            due_date=request_obj.due_date.strftime("%b %d, %Y") if request_obj.due_date else "Not set",
            engagement=request_obj.get_engagement_type_display(),
            description=request_obj.description or "No additional details provided.",
        )

        body = quote("Hello Team,\n\nPlease find the request details below:\n\n" + body_content + "\n\nRegards,\n" + (request.user.get_full_name() or request.user.username))

        outlook_url = f"mailto:{recipients}?subject={subject}&body={body}"
        messages.info(request, "Drafting email in your default mail client…")
        return render(
            request,
            "hub/outlook_redirect.html",
            {"mailto_url": outlook_url},
        )


class RequestExportCSVView(AdminRequiredMixin, LoginRequiredMixin, View):
    """Allow administrators to export all requests to a CSV download."""

    columns = (
        "Reference",
        "Account",
        "Account Manager",
        "Account Manager Email",
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


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "hub/notifications.html"
    context_object_name = "notifications"

    def get_queryset(self):
        return self.request.user.notifications.all()


class NotificationReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        notification.mark_read()
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("hub:notifications")))
