from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CaseInsensitiveUsernameBackend(ModelBackend):
    """Authenticate using usernames without enforcing case sensitivity."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None

        normalized_username = username.strip()
        if not normalized_username:
            return None

        lookup = {f"{UserModel.USERNAME_FIELD}__iexact": normalized_username}
        try:
            user = UserModel._default_manager.get(**lookup)
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            user = (
                UserModel._default_manager.filter(**lookup)
                .order_by(UserModel.USERNAME_FIELD)
                .first()
            )

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
