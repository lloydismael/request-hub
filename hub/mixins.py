from django.contrib.auth.mixins import UserPassesTestMixin

from accounts.models import User


class RoleRequiredMixin(UserPassesTestMixin):
    required_role: str = ""
    required_roles: set[str] | None = None

    def test_func(self):
        roles = set(self.required_roles or set())
        if self.required_role:
            roles.add(self.required_role)
        if not roles:
            return False
        return self.request.user.role in roles


class RequestorRequiredMixin(RoleRequiredMixin):
    required_roles = set(getattr(User, "REQUEST_CREATOR_ROLES", User.REQUESTOR_ROLES))


class EngineerRequiredMixin(RoleRequiredMixin):
    required_role = User.Roles.ENGINEER


class AdminRequiredMixin(RoleRequiredMixin):
    required_role = User.Roles.ADMIN


class AdminOrPmEsgRequiredMixin(RoleRequiredMixin):
    required_roles = {User.Roles.ADMIN, User.Roles.PM_ESG}


class AdminOrEngineerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role in {User.Roles.ADMIN, User.Roles.PM_ESG, User.Roles.ENGINEER}
