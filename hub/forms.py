from django import forms

from django.utils import timezone

from typing import Iterable, List

from accounts.models import User
from .constants import ACCOUNT_NAME_SUGGESTIONS
from .models import Account, Request, StatusLog


class AvatarSelect(forms.Select):
    """Select widget that stores avatar metadata on each option."""

    def __init__(self, *args, **kwargs):
        self.avatar_mapping = {}
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        option_value = option.get("value")
        if option_value:
            meta = self.avatar_mapping.get(str(option_value))
            if meta:
                if meta.get("url"):
                    option["attrs"]["data-avatar"] = meta["url"]
                if meta.get("initial"):
                    option["attrs"]["data-initial"] = meta["initial"]
        return option


def _build_avatar_mapping(users):
    mapping = {}
    for user in users:
        display_name = (user.get_full_name() or user.username or "?").strip()
        initial = display_name[:1].upper() if display_name else "?"
        avatar_url = ""
        if getattr(user, "profile_photo", None):
            try:
                avatar_url = user.profile_photo.url
            except ValueError:
                avatar_url = ""
        mapping[str(user.pk)] = {"url": avatar_url, "initial": initial}
    return mapping


def _user_display(user):
    full_name = user.get_full_name().strip() if user.get_full_name() else ""
    return full_name or user.username


class RequestForm(forms.ModelForm):
    account_name = forms.CharField(
        label="Account Name",
        help_text="Select from the list or type a new account name.",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "list": "account-name-options",
                "placeholder": "Start typing to search accounts",
                "autocomplete": "off",
            }
        ),
    )
    needed_by = forms.DateField(
        label="Request Date",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    engineer = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=True,
        widget=AvatarSelect(attrs={"class": "form-select", "data-avatar-select": "true"}),
        label="Preferred Engineer",
        empty_label="Select preferred engineer",
        error_messages={"required": "Please choose a preferred engineer for this request."},
    )

    class Meta:
        model = Request
        fields = [
            "account_name",
            "needed_by",
            "product_category",
            "engagement_type",
            "description",
            "engineer",
        ]
        widgets = {
            "product_category": forms.Select(attrs={"class": "form-select"}),
            "engagement_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        engineer_qs = User.objects.filter(role=User.Roles.ENGINEER).order_by("first_name", "last_name")
        self.fields["engineer"].queryset = engineer_qs
        widget = self.fields["engineer"].widget
        if isinstance(widget, AvatarSelect):
            widget.avatar_mapping = _build_avatar_mapping(engineer_qs)
        self.fields["engineer"].label_from_instance = _user_display
        if self.instance.pk:
            self.fields["account_name"].initial = self.instance.account.name
        due_field = self.fields["needed_by"]
        if self.instance.pk and self.instance.start_date:
            due_field.initial = self.instance.start_date
        else:
            due_field.initial = timezone.now().date()

        existing_accounts = Account.objects.order_by("name").values_list("name", flat=True)
        combined = []
        seen = set()
        for raw_name in list(ACCOUNT_NAME_SUGGESTIONS) + list(existing_accounts):
            cleaned = (raw_name or "").strip()
            if not cleaned:
                continue
            normalized = cleaned.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            combined.append(cleaned)
        self.account_name_suggestions = tuple(combined)

    def clean_account_name(self):
        value = self.cleaned_data["account_name"].strip()
        if not value:
            raise forms.ValidationError("Account name is required.")
        return value

    def clean_needed_by(self):
        request_date = self.cleaned_data.get("needed_by")
        if not request_date:
            return request_date
        today = timezone.now().date()
        if request_date < today:
            raise forms.ValidationError("Select today or a future date for the request.")
        return request_date

    def save(self, commit=True):
        account_name = self.cleaned_data["account_name"]
        account, _ = Account.objects.get_or_create(name=account_name)
        self.instance.account = account
        self.instance.engineer = self.cleaned_data.get("engineer")
        request_date = self.cleaned_data.get("needed_by")
        if request_date:
            self.instance.start_date = request_date
        return super().save(commit=commit)


class RequestAdminForm(forms.ModelForm):
    engineer = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Roles.ENGINEER),
        required=False,
        widget=AvatarSelect(attrs={"class": "form-select", "data-avatar-select": "true"}),
    )
    backup_engineer = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Roles.ENGINEER),
        required=False,
        widget=AvatarSelect(attrs={"class": "form-select", "data-avatar-select": "true"}),
        label="Backup Engineer",
        empty_label="Select backup engineer (optional)",
    )

    class Meta:
        model = Request
        fields = [
            "priority",
            "status",
            "engineer",
            "backup_engineer",
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
        widget = self.fields["engineer"].widget
        if isinstance(widget, AvatarSelect):
            widget.avatar_mapping = _build_avatar_mapping(self.fields["engineer"].queryset)
        self.fields["engineer"].label_from_instance = _user_display
        
        # Setup backup engineer field
        self.fields["backup_engineer"].queryset = self.fields["backup_engineer"].queryset.order_by("first_name", "last_name")
        backup_widget = self.fields["backup_engineer"].widget
        if isinstance(backup_widget, AvatarSelect):
            backup_widget.avatar_mapping = _build_avatar_mapping(self.fields["backup_engineer"].queryset)
        self.fields["backup_engineer"].label_from_instance = _user_display
        
        due_field = self.fields["due_date"]
        due_field.required = False
        due_field.help_text = "Leave blank to keep the SLA-based due date."


class RequestStatusForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ["status", "end_date"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        end_date = cleaned_data.get("end_date")
        if status == Request.Status.ONGOING:
            # Reset end date before model validation so toggling back to ongoing passes clean()
            self.instance.end_date = None
            cleaned_data["end_date"] = None
        elif status == Request.Status.COMPLETED:
            if not end_date:
                self.add_error("end_date", "Select the completion date before closing the ticket.")
            else:
                self.instance.end_date = end_date
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.status == Request.Status.ONGOING:
            instance.end_date = None
        else:
            instance.end_date = self.cleaned_data.get("end_date")
        if commit:
            instance.save()
        return instance


class StatusLogForm(forms.ModelForm):
    class Meta:
        model = StatusLog
        fields = ["message"]
        labels = {"message": "Add status update"}
        widgets = {
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Add an update"}),
        }

    def clean_message(self):
        message = self.cleaned_data.get("message", "").strip()
        if not message:
            raise forms.ValidationError("Message cannot be empty.")
        return message


class AdminRequestFilterForm(forms.Form):
    reference_code = forms.CharField(
        label="ID",
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-sm", "placeholder": "Search ID"}
        ),
    )
    account = forms.ModelChoiceField(
        label="Account",
        required=False,
        queryset=Account.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    account_manager = forms.ModelChoiceField(
        label="Requestor",
        required=False,
        queryset=User.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    engineer = forms.ModelChoiceField(
        label="Assigned Engineer",
        required=False,
        queryset=User.objects.none(),
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    priority = forms.ChoiceField(
        label="Priority",
        required=False,
        choices=[("", "All priorities"), *Request.Priority.choices],
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    status = forms.ChoiceField(
        label="Status",
        required=False,
        choices=[("", "All statuses"), *Request.Status.choices],
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )
    created_from = forms.DateField(
        label="Created From",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
    )
    created_to = forms.DateField(
        label="Created To",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
    )
    end_from = forms.DateField(
        label="End Date From",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
    )
    end_to = forms.DateField(
        label="End Date To",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
    )
    days_min = forms.IntegerField(
        label="Days Min",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control form-control-sm", "placeholder": "≥"}),
    )
    days_max = forms.IntegerField(
        label="Days Max",
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control form-control-sm", "placeholder": "≤"}),
    )
    due_from = forms.DateField(
        label="Due Date From",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
    )
    due_to = forms.DateField(
        label="Due Date To",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = Account.objects.order_by("name")
        self.fields["account"].empty_label = "All accounts"
        requestor_qs = User.objects.filter(role=User.Roles.REQUESTOR).order_by("first_name", "last_name")
        self.fields["account_manager"].queryset = requestor_qs
        self.fields["account_manager"].empty_label = "All requestors"
        self.fields["account_manager"].label_from_instance = _user_display
        engineer_qs = User.objects.filter(role=User.Roles.ENGINEER).order_by("first_name", "last_name")
        self.fields["engineer"].queryset = engineer_qs
        self.fields["engineer"].empty_label = "All engineers"
        self.fields["engineer"].label_from_instance = _user_display

    def filter_queryset(self, queryset):
        if not self.is_valid():
            return queryset
        data = self.cleaned_data
        if data.get("reference_code"):
            queryset = queryset.filter(reference_code__icontains=data["reference_code"].strip())
        if data.get("account"):
            queryset = queryset.filter(account=data["account"])
        if data.get("account_manager"):
            queryset = queryset.filter(requestor=data["account_manager"])
        if data.get("engineer"):
            queryset = queryset.filter(engineer=data["engineer"])
        if data.get("priority"):
            queryset = queryset.filter(priority=data["priority"])
        if data.get("status"):
            queryset = queryset.filter(status=data["status"])
        if data.get("created_from"):
            queryset = queryset.filter(created_at__date__gte=data["created_from"])
        if data.get("created_to"):
            queryset = queryset.filter(created_at__date__lte=data["created_to"])
        if data.get("end_from"):
            queryset = queryset.filter(end_date__gte=data["end_from"])
        if data.get("end_to"):
            queryset = queryset.filter(end_date__lte=data["end_to"])
        if data.get("due_from"):
            queryset = queryset.filter(due_date__gte=data["due_from"])
        if data.get("due_to"):
            queryset = queryset.filter(due_date__lte=data["due_to"])
        return queryset

    def filter_sequence(self, requests: Iterable[Request]) -> List[Request]:
        if not self.is_valid():
            return list(requests)
        data = self.cleaned_data
        results = list(requests)
        days_min = data.get("days_min")
        if days_min is not None:
            results = [req for req in results if req.days_since_creation >= days_min]
        days_max = data.get("days_max")
        if days_max is not None:
            results = [req for req in results if req.days_since_creation <= days_max]
        return results

    def has_active_filters(self) -> bool:
        if not self.is_valid():
            return False
        for value in self.cleaned_data.values():
            if value not in {None, ""}:
                return True
        return False


class AccountManagementForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Account name"}),
        }
        labels = {
            "name": "Account Name",
        }

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Account name cannot be blank.")
        return name
