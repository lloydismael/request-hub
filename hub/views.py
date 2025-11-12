from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from accounts.models import User

from .forms import RequestAdminForm, RequestForm, StatusLogForm
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
