from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

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
    current_password = forms.CharField(
        label="Current password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"}),
        help_text="Enter your current password to set a new one.",
    )
    new_password1 = forms.CharField(
        label="New password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label="Confirm new password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
        help_text="Enter the same password as before for verification.",
    )

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

    field_order = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "profile_photo",
        "current_password",
        "new_password1",
        "new_password2",
    ]

    def clean(self):
        cleaned_data = super().clean()
        current_password = cleaned_data.get("current_password")
        new_password1 = cleaned_data.get("new_password1")
        new_password2 = cleaned_data.get("new_password2")
        user = self.instance

        if new_password1 or new_password2:
            if not current_password:
                self.add_error("current_password", "Enter your current password to set a new one.")
            elif not user.check_password(current_password):
                self.add_error("current_password", "Current password is incorrect.")

            if not new_password1:
                self.add_error("new_password1", "Enter a new password.")
            if new_password1 and new_password1 != new_password2:
                self.add_error("new_password2", "Passwords do not match.")

            if new_password1 and not self.errors.get("new_password1"):
                try:
                    password_validation.validate_password(new_password1, user)
                except ValidationError as exc:
                    self.add_error("new_password1", exc)
        elif current_password:
            self.add_error("new_password1", "Enter a new password.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password1")

        if new_password:
            user.set_password(new_password)

        if commit:
            user.save()
            self.save_m2m()

        return user


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
