from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import User

ROLE_LABELS = {
    User.Roles.ADMIN: "Admin",
    User.Roles.ENGINEER: "Engineer",
    User.Roles.REQUESTOR: "Account Manager",
}

ROLE_CHOICES = [(key, label) for key, label in ROLE_LABELS.items()]

ROLE_ALIAS_MAP = {
    User.Roles.ADMIN: {
        "admin": "Admin",
        "admin1": "Admin1",
    },
    User.Roles.ENGINEER: {
        "admin": "engineer_admin",
        "admin1": "engineer_admin1",
    },
    User.Roles.REQUESTOR: {
        "admin": "account_admin",
        "admin1": "manager_admin1",
    },
}

ROLE_DEFAULT_USERNAMES = {role: aliases.get("admin", "") for role, aliases in ROLE_ALIAS_MAP.items()}


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number", "profile_photo"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "profile_photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class RoleAuthenticationForm(AuthenticationForm):
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label="Sign in as",
    )

    def __init__(self, request=None, *args, **kwargs):
        role_initial = kwargs.pop("role_initial", None)
        username_field = User.USERNAME_FIELD
        data = kwargs.get("data")
        if data:
            data = data.copy()
            role_value = data.get("role") or role_initial
            username_input = data.get(username_field)
            if role_value and username_input:
                alias_map = ROLE_ALIAS_MAP.get(role_value, {})
                alias = alias_map.get(username_input.strip().lower())
                if alias:
                    data[username_field] = alias
            kwargs["data"] = data

        super().__init__(request=request, *args, **kwargs)

        if role_initial and role_initial in dict(ROLE_CHOICES):
            self.fields["role"].initial = role_initial
        self.fields["username"].widget.attrs.update({"class": "form-control"})
        self.fields["password"].widget.attrs.update({"class": "form-control"})

    def confirm_login_allowed(self, user):
        selected_role = self.cleaned_data.get("role")
        if selected_role and user.role != selected_role:
            raise forms.ValidationError(
                "Selected role does not match the provided credentials.",
                code="invalid_role",
            )
        super().confirm_login_allowed(user)
