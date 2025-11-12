from django.contrib.auth.mixins import UserPassesTestMixin

from accounts.models import User


class RoleRequiredMixin(UserPassesTestMixin):
    required_role: str = ""

    def test_func(self):
        if not self.required_role:
            return False
        return self.request.user.role == self.required_role


class RequestorRequiredMixin(RoleRequiredMixin):
    required_role = User.Roles.REQUESTOR


class EngineerRequiredMixin(RoleRequiredMixin):
    required_role = User.Roles.ENGINEER


class AdminRequiredMixin(RoleRequiredMixin):
    required_role = User.Roles.ADMIN
