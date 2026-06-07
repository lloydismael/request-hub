from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, UpdateView

from accounts.middleware import FORCE_PASSWORD_CHANGE_SESSION_KEY
from accounts.models import StoredFile, User

from .forms import (
    ProfileForm,
    ROLE_CHOICES,
    ROLE_DEFAULT_USERNAMES,
    ROLE_LABELS,
    RoleAuthenticationForm,
)


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile_form.html"
    success_url = reverse_lazy("accounts:update")

    def get_object(self):
        return self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["is_admin"] = self.request.user.role == "admin"
        return kwargs

    def post(self, request, *args, **kwargs):
        # Settings tab has its own lightweight POST — handle before the main form
        if request.POST.get("save_settings"):
            user = request.user
            user.show_chatbot = request.POST.get("show_chatbot") == "1"
            user.idle_timeout_enabled = request.POST.get("idle_timeout_enabled") == "1"
            user.save(update_fields=["show_chatbot", "idle_timeout_enabled"])
            messages.success(request, "Settings saved.")
            return redirect(reverse_lazy("accounts:update") + "#settings")
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        password_changed = bool(form.cleaned_data.get("new_password1"))
        delete_photo_requested = form.data.get("delete_photo")
        save_banner_requested = form.data.get("save_banner")
        photo_deleted = False

        if delete_photo_requested:
            existing_photo = form.instance.profile_photo
            if existing_photo:
                existing_photo.delete(save=False)
                photo_deleted = True
            form.instance.profile_photo = None
            if "profile_photo" in form.cleaned_data:
                form.cleaned_data["profile_photo"] = None

        # When saving banner, also propagate the hidden field value from POST
        if save_banner_requested:
            banner_val = form.data.get("banner_gradient", "").strip()
            valid_keys = {"blue", "sunset", "forest", "crimson", "slate", "aurora", "rose", "teal"}
            if banner_val in valid_keys:
                form.instance.banner_gradient = banner_val

        response = super().form_valid(form)
        user = self.request.user
        user.profile_completed = True
        user.save(update_fields=["profile_completed"])
        if password_changed:
            self.request.session.pop(FORCE_PASSWORD_CHANGE_SESSION_KEY, None)
            update_session_auth_hash(self.request, self.object)
        message_details = []
        if password_changed:
            message_details.append("Your password has been changed")
        if photo_deleted:
            message_details.append("Profile photo deleted")
        if message_details:
            details_text = " ".join(f"{detail}." for detail in message_details)
            messages.success(self.request, f"Profile updated successfully. {details_text}")
        else:
            messages.success(self.request, "Profile updated successfully.")
        return response


class LandingView(TemplateView):
    template_name = "landing.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("hub:dashboard")
        return redirect("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        descriptions = {
            User.Roles.ADMIN: "Oversee requests, assign engineers, and close engagements.",
            User.Roles.PM_ESG: "Manage requests like administrators, coordinate engineers, and create tickets without user-management access.",
            User.Roles.ENGINEER: "Review assigned tickets, respond to updates, and act on SLAs.",
            User.Roles.ON_HOLD: "Retain engineer access to previously assigned work while staying unavailable for new assignments.",
            User.Roles.REQUESTOR: "Create new customer requests and monitor progress.",
            User.Roles.REQUESTOR_ESS: "Submit customer requests without Support engagements and track progress.",
            User.Roles.PM_ESS: "Oversee Requestor-ESS requests, create tickets, and track status across accounts.",
        }
        context["role_cards"] = [
            {
                "role": role,
                "label": ROLE_LABELS[role],
                "description": descriptions.get(role, ""),
            }
            for role, _ in ROLE_CHOICES
        ]
        context["default_username"] = "Admin"
        context["default_password"] = getattr(settings, "DEFAULT_USER_PASSWORD", "@Password")
        context["role_default_usernames"] = ROLE_DEFAULT_USERNAMES
        return context


class RoleLoginView(LoginView):
    authentication_form = RoleAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def confirm_login_allowed(self, user):
        selected_role = self.cleaned_data.get("role")
        if selected_role and user.role != selected_role:
            raise forms.ValidationError(
                "Selected role does not match the provided credentials.",
                code="invalid_role",
            )
        super().confirm_login_allowed(user)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Login successful. Redirecting to your dashboard…", extra_tags="login-success")
        return response


class StoredFileServeView(LoginRequiredMixin, View):
    def get(self, request, name):
        stored_file = get_object_or_404(StoredFile, name=name)
        if not stored_file.data:
            raise Http404
        response = HttpResponse(stored_file.data, content_type=stored_file.content_type or "application/octet-stream")
        filename = stored_file.original_name or name.split("/")[-1]
        response["Content-Disposition"] = f"inline; filename=\"{filename}\""
        response["Cache-Control"] = "private, max-age=86400"
        return response
