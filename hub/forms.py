from django import forms

from accounts.models import User

from .constants import ACCOUNT_MANAGER_NAMES
from .models import Account, Request


class RequestForm(forms.ModelForm):
    account_name = forms.CharField(label="Account Name", widget=forms.TextInput(attrs={"class": "form-control"}))
    account_manager = forms.ChoiceField(
        choices=[(name, name) for name in ACCOUNT_MANAGER_NAMES],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Request
        fields = [
            "account_name",
            "account_manager",
            "product_category",
            "priority",
            "engagement_type",
            "description",
        ]
        widgets = {
            "product_category": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "engagement_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["account_name"].initial = self.instance.account.name

    def clean_account_name(self):
        value = self.cleaned_data["account_name"].strip()
        if not value:
            raise forms.ValidationError("Account name is required.")
        return value

    def save(self, commit=True):
        account_name = self.cleaned_data["account_name"]
        account, _ = Account.objects.get_or_create(name=account_name)
        self.instance.account = account
        return super().save(commit=commit)


class RequestAdminForm(forms.ModelForm):
    engineer = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Roles.ENGINEER),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Request
        fields = [
            "priority",
            "status",
            "engineer",
            "due_date",
            "end_date",
            "description",
        ]
        widgets = {
            "priority": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["engineer"].queryset = self.fields["engineer"].queryset.order_by("first_name", "last_name")
