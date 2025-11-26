import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.forms import modelformset_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, DeleteView, ListView, TemplateView, UpdateView
from urllib.parse import quote

from accounts.forms import UserManagementForm
from accounts.models import User

from .forms import RequestAdminForm, RequestForm, RequestStatusForm, StatusLogForm
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
            self._notify_status_update(log)
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

    def _notify_status_update(self, log):
        request_obj = log.request
        author = log.author
        author_name = author.get_full_name() or author.username
        recipients = {}

        if request_obj.engineer:
            recipients[request_obj.engineer.pk] = request_obj.engineer
        if request_obj.requestor:
            recipients[request_obj.requestor.pk] = request_obj.requestor

        for admin in User.objects.filter(role=User.Roles.ADMIN):
            recipients[admin.pk] = admin

        for user in recipients.values():
            if user.pk == author.pk:
                continue
            Notification.objects.create(
                recipient=user,
                message=f"{author_name} posted an update on {request_obj.reference_code or 'a request'}.",
                related_request=request_obj,
            )


class RequestAdminUpdateView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Request
    form_class = RequestAdminForm
    template_name = "hub/request_admin_form.html"
    success_url = reverse_lazy("hub:dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Request updated.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        referer = self.request.META.get("HTTP_REFERER")
        fallback = reverse("hub:dashboard")
        if not referer or referer == self.request.build_absolute_uri():
            context["back_url"] = fallback
        else:
            context["back_url"] = referer
        context["hide_sign_in_nav"] = True
        return context


class RequestUpdateView(LoginRequiredMixin, UpdateView):
    model = Request
    form_class = RequestForm
    template_name = "hub/request_update.html"
    success_url = reverse_lazy("hub:dashboard")

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
        messages.success(self.request, "Request updated.")
        return super().form_valid(form)


class RequestStatusUpdateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        request_obj = get_object_or_404(
            Request.objects.select_related("engineer", "requestor"),
            pk=pk,
        )

        if request.user.role != User.Roles.ENGINEER or request_obj.engineer_id != request.user.id:
            messages.error(request, "You are not allowed to update this request's status.")
            return redirect("hub:request-detail", pk=pk)

        form = RequestStatusForm(request.POST, instance=request_obj)
        if form.is_valid():
            form.save()
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


class UserManagementView(AdminRequiredMixin, LoginRequiredMixin, View):
    template_name = "hub/management.html"
    formset_class = modelformset_factory(User, form=UserManagementForm, extra=1, can_delete=True)

    def get_queryset(self):
        return User.objects.order_by("date_joined", "username")

    def get(self, request, *args, **kwargs):
        formset = self.formset_class(queryset=self.get_queryset())
        self._prepare_formset(formset)
        return render(request, self.template_name, self._build_context(formset))

    def post(self, request, *args, **kwargs):
        formset = self.formset_class(request.POST, queryset=self.get_queryset())
        self._prepare_formset(formset)
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
                return render(request, self.template_name, self._build_context(formset))

            if current_admins + admin_delta <= 0:
                if admin_removal_candidates:
                    form, field = admin_removal_candidates[0]
                    if field == "delete":
                        form.add_error("DELETE", "At least one administrator must remain.")
                    else:
                        form.add_error("role", "At least one administrator must remain.")
                else:
                    messages.error(request, "At least one administrator must remain.")
                return render(request, self.template_name, self._build_context(formset))

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

        return render(request, self.template_name, self._build_context(formset))

    def _build_context(self, formset):
        return {
            "formset": formset,
            "total_users": User.objects.count(),
        }

    @staticmethod
    def _prepare_formset(formset):
        for form in formset:
            delete_field = form.fields.get("DELETE")
            if delete_field:
                existing_class = delete_field.widget.attrs.get("class", "")
                delete_field.widget.attrs["class"] = (existing_class + " form-check-input").strip()


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
