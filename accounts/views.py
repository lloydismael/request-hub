from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from accounts.models import User

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
    success_url = reverse_lazy("hub:dashboard")

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        password_changed = bool(form.cleaned_data.get("new_password1"))
        response = super().form_valid(form)
        user = self.request.user
        user.profile_completed = True
        user.save(update_fields=["profile_completed"])
        if password_changed:
            update_session_auth_hash(self.request, self.object)
            messages.success(self.request, "Profile updated successfully. Your password has been changed.")
        else:
            messages.success(self.request, "Profile updated successfully.")
        return response


class LandingView(TemplateView):
    template_name = "landing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        descriptions = {
            User.Roles.ADMIN: "Oversee requests, assign engineers, and close engagements.",
            User.Roles.ENGINEER: "Review assigned tickets, respond to updates, and act on SLAs.",
            User.Roles.REQUESTOR: "Create new customer requests and monitor progress.",
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
        context["default_password"] = "Admin"
        context["role_default_usernames"] = ROLE_DEFAULT_USERNAMES
        return context


class RoleLoginView(LoginView):
    authentication_form = RoleAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        role_param = self.request.GET.get("role") or self.request.POST.get("role")
        valid_roles = {choice for choice, _ in ROLE_CHOICES}
        if role_param in valid_roles:
            kwargs["role_initial"] = role_param
        return kwargs
