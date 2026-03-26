from django import forms

from django.utils import timezone

from typing import Iterable, List

from django.db.models import Q

from accounts.models import User
from .models import Account, EngineerActivityLog, Request, StatusLog


class AvatarSelect(forms.Select):
    """Select widget that stores avatar metadata on each option."""

    def __init__(self, *args, **kwargs):
        self.avatar_mapping = {}
        self.option_group_mapping = {}
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
            group = self.option_group_mapping.get(str(option_value))
            if group:
                option["attrs"]["data-role-group"] = group
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
    PROJECT_MANAGER_DISPLAY_NAMES = (
        "Jeram C. Zamora",
        "Marfelie B. Barcenas",
        "Princess Nicole D. Nacianceno",
    )

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
    deployment_start = forms.DateField(
        label="Deployment Start",
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "data-deployment-start": "true",
            }
        ),
    )
    deployment_end = forms.DateField(
        label="Deployment End",
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "data-deployment-end": "true",
            }
        ),
    )
    priority = forms.ChoiceField(
        label="Priority",
        choices=Request.Priority.choices,
        required=False,
        widget=forms.Select(attrs={"class": "form-select", "data-priority-select": "true"}),
    )
    engineer = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=AvatarSelect(attrs={"class": "form-select", "data-avatar-select": "true"}),
        label="Preferred Engineer",
        empty_label="Select preferred engineer",
    )
    backup_engineer = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=AvatarSelect(attrs={"class": "form-select", "data-avatar-select": "true"}),
        label="Backup Engineer",
        empty_label="Select backup engineer (optional)",
    )

    class Meta:
        model = Request
        fields = [
            "account_name",
            "needed_by",
            "product_category",
            "engagement_type",
            "priority",
            "description",
            "engineer",
            "backup_engineer",
        ]
        widgets = {
            "product_category": forms.Select(attrs={"class": "form-select"}),
            "engagement_type": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select", "data-priority-select": "true"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, actor_role=None, **kwargs):
        self.actor_role = actor_role
        super().__init__(*args, **kwargs)
        self.project_manager_ids = set()
        include_backup = actor_role == User.Roles.ENGINEER
        if not include_backup:
            self.fields.pop("backup_engineer", None)
        desired_order = [
            "account_name",
            "needed_by",
            "product_category",
            "engagement_type",
            "deployment_start",
            "deployment_end",
            "priority",
            "description",
            "engineer",
        ]
        if include_backup:
            desired_order.append("backup_engineer")
        self.order_fields(desired_order)
        engineer_qs = User.objects.filter(role=User.Roles.ENGINEER).order_by("first_name", "last_name")
        project_manager_qs = User.objects.filter(
            (Q(first_name__icontains="Jeram") & Q(last_name__icontains="Zamora"))
            | (Q(first_name__icontains="Marfelie") & Q(last_name__icontains="Barcenas"))
            | (Q(first_name__icontains="Princess") & Q(last_name__icontains="Nacianceno"))
        ).order_by("first_name", "last_name")
        self.project_manager_ids = set(project_manager_qs.values_list("id", flat=True))

        requestor_roles = {User.Roles.REQUESTOR, User.Roles.REQUESTOR_ESS, User.Roles.PM_ESS}
        is_requestor_form = actor_role in requestor_roles
        all_assignee_ids = set(engineer_qs.values_list("id", flat=True)) | self.project_manager_ids
        assignee_qs = (
            User.objects.filter(id__in=all_assignee_ids).order_by("first_name", "last_name")
            if is_requestor_form
            else engineer_qs
        )

        engineer_field = self.fields["engineer"]
        engineer_field.queryset = assignee_qs
        widget = engineer_field.widget
        if isinstance(widget, AvatarSelect):
            widget.avatar_mapping = _build_avatar_mapping(assignee_qs)
            if is_requestor_form:
                widget.option_group_mapping = {
                    str(user_id): ("project_manager" if user_id in self.project_manager_ids else "engineer")
                    for user_id in all_assignee_ids
                }
        engineer_field.label_from_instance = _user_display
        if actor_role == User.Roles.ENGINEER:
            engineer_field.label = "Turn Over Request"
            engineer_field.empty_label = "Keep current assignment"
        else:
            engineer_field.label = "Preferred Engineer"
            engineer_field.empty_label = "Select preferred engineer"

        engagement_value = ""
        if self.is_bound:
            engagement_value = (
                self.data.get(self.add_prefix("engagement_type"))
                or self.data.get("engagement_type")
                or ""
            )
        elif self.instance.pk and self.instance.engagement_type:
            engagement_value = self.instance.engagement_type

        if is_requestor_form:
            engineer_widget_attrs = engineer_field.widget.attrs
            engineer_widget_attrs["data-engineer-label"] = "Preferred Engineer"
            engineer_widget_attrs["data-project-manager-label"] = "Preferred Project Manager"
            engineer_widget_attrs["data-engineer-empty-label"] = "Select preferred engineer"
            engineer_widget_attrs["data-project-manager-empty-label"] = "Select preferred project manager"
            engineer_widget_attrs["data-project-management-value"] = Request.Engagement.PROJECT_MANAGEMENT
            if engagement_value == Request.Engagement.PROJECT_MANAGEMENT:
                engineer_field.label = "Preferred Project Manager"
                engineer_field.empty_label = "Select preferred project manager"
        if include_backup:
            backup_field = self.fields["backup_engineer"]
            backup_field.queryset = engineer_qs
            backup_widget = backup_field.widget
            if isinstance(backup_widget, AvatarSelect):
                backup_widget.avatar_mapping = _build_avatar_mapping(engineer_qs)
            backup_field.label_from_instance = _user_display
        priority_field = self.fields["priority"]
        if not self.is_bound:
            if self.instance.pk and self.instance.priority:
                priority_field.initial = self.instance.priority
            else:
                priority_field.initial = Request.Priority.MEDIUM
        priority_widget = priority_field.widget
        if self.is_bound:
            default_priority = getattr(self.instance, "priority", None) or Request.Priority.MEDIUM
        else:
            default_priority = priority_field.initial or Request.Priority.MEDIUM
        priority_widget.attrs["data-default-priority"] = default_priority
        if self.instance.pk:
            self.fields["account_name"].initial = self.instance.account.name
        due_field = self.fields["needed_by"]
        today = timezone.now().date()
        if self.instance.pk and self.instance.start_date:
            due_field.initial = self.instance.start_date

        else:
            due_field.initial = today
        due_field.widget.attrs.pop("min", None)

        engagement_field = self.fields["engagement_type"]
        if actor_role in {User.Roles.REQUESTOR_ESS, User.Roles.PM_ESS}:
            filtered_choices = [
                choice
                for choice in engagement_field.choices
                if choice[0] != Request.Engagement.SUPPORT
            ]
            if self.instance.pk and self.instance.engagement_type == Request.Engagement.SUPPORT:
                filtered_choices.append((Request.Engagement.SUPPORT, Request.Engagement.SUPPORT.label))
            engagement_field.choices = filtered_choices

        deployment_start_field = self.fields["deployment_start"]
        deployment_end_field = self.fields["deployment_end"]
        if self.instance.pk and self.instance.engagement_type == Request.Engagement.DEPLOYMENT:
            deployment_start_field.initial = self.instance.start_date
            deployment_end_field.initial = self.instance.due_date or self.instance.start_date
        elif not self.is_bound:
            deployment_start_field.initial = today
            deployment_end_field.initial = today

        existing_accounts = Account.objects.order_by("name").values_list("name", flat=True)
        suggestions = []
        for raw_name in existing_accounts:
            cleaned = (raw_name or "").strip()
            if not cleaned:
                continue
            suggestions.append(cleaned)
        self.account_name_suggestions = tuple(suggestions)

        if self.is_bound and self.errors:
            for name, field in self.fields.items():
                if name in self.errors:
                    widget = field.widget
                    existing_classes = widget.attrs.get("class", "")
                    class_list = existing_classes.split()
                    if "is-invalid" not in class_list:
                        widget.attrs["class"] = (existing_classes + " is-invalid").strip()

    def clean(self):
        cleaned_data = super().clean()

        # Enforce per-engineer ongoing capacity rules during turn-over by engineers.
        # If the target engineer already carries a deployment, they are capped at 3 ongoing requests.
        # Otherwise they can handle up to 5 ongoing requests (even when receiving the first deployment).
        if self.actor_role == User.Roles.ENGINEER:
            new_engineer = cleaned_data.get("engineer")
            if new_engineer and new_engineer != self.instance.engineer:
                ongoing_qs = Request.objects.filter(engineer=new_engineer, status=Request.Status.ONGOING)
                if self.instance.pk:
                    ongoing_qs = ongoing_qs.exclude(pk=self.instance.pk)

                has_deployment = ongoing_qs.filter(engagement_type=Request.Engagement.DEPLOYMENT).exists()
                capacity = 3 if has_deployment else 5
                current_load = ongoing_qs.count()

                if current_load >= capacity:
                    name = new_engineer.get_full_name() or new_engineer.username or "Engineer"
                    if has_deployment:
                        msg = (
                            f"{name} is at the deployment limit (max 3 ongoing while a deployment is active). "
                            "Choose another engineer or wait until a deployment is completed."
                        )
                    else:
                        msg = f"{name} already has {current_load} ongoing requests (limit {capacity}). Choose another engineer."
                    self.add_error("engineer", msg)

        return cleaned_data

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
        return request_date

    def clean(self):
        cleaned_data = super().clean()
        engagement = cleaned_data.get("engagement_type")
        priority = cleaned_data.get("priority")
        if engagement == Request.Engagement.SUPPORT:
            if not priority:
                self.add_error("priority", "Select the priority for support requests.")
        else:
            existing_priority = self.instance.priority if getattr(self.instance, "priority", None) else Request.Priority.MEDIUM
            cleaned_data["priority"] = existing_priority or Request.Priority.MEDIUM

        deployment_start = cleaned_data.get("deployment_start")
        deployment_end = cleaned_data.get("deployment_end")
        if engagement == Request.Engagement.DEPLOYMENT:
            if not deployment_start:
                self.add_error("deployment_start", "Select the deployment start date.")
            if not deployment_end:
                self.add_error("deployment_end", "Select the deployment end date.")
            if deployment_start and deployment_end and deployment_end < deployment_start:
                self.add_error("deployment_end", "Deployment end date cannot be earlier than the start date.")
            if deployment_start:
                cleaned_data["needed_by"] = deployment_start
        else:
            cleaned_data["deployment_start"] = None
            cleaned_data["deployment_end"] = None
        return cleaned_data

    def clean_engineer(self):
        engineer = self.cleaned_data.get("engineer")
        if not engineer:
            return engineer

        engagement = self.cleaned_data.get("engagement_type") or getattr(self.instance, "engagement_type", None)
        if engagement == Request.Engagement.PROJECT_MANAGEMENT and engineer.pk not in self.project_manager_ids:
            raise forms.ValidationError("Select a preferred project manager from the approved list.")

        ongoing_requests = Request.objects.filter(
            engineer=engineer,
            status=Request.Status.ONGOING,
        )

        if self.instance.pk:
            ongoing_requests = ongoing_requests.exclude(pk=self.instance.pk)

        deployment_start = self.cleaned_data.get("deployment_start")
        deployment_end = self.cleaned_data.get("deployment_end")
        max_allowed = 5
        if engagement == Request.Engagement.DEPLOYMENT and deployment_start and deployment_end:
            base_filter = Q(start_date__lte=deployment_end)
            overlap_filter = base_filter & (Q(due_date__gte=deployment_start) | Q(due_date__isnull=True))
            overlapping_deployments = ongoing_requests.filter(
                engagement_type=Request.Engagement.DEPLOYMENT
            ).filter(overlap_filter)
            if overlapping_deployments.exists():
                max_allowed = 3

        if ongoing_requests.count() >= max_allowed:
            if max_allowed == 3:
                raise forms.ValidationError(
                    "This engineer already has three overlapping deployment assignments for the selected window. Choose another engineer or adjust the deployment dates.",
                )
            raise forms.ValidationError(
                "This engineer already has five ongoing requests. Please select another engineer.",
            )

        return engineer

    def save(self, commit=True):
        account_name = self.cleaned_data["account_name"]
        account, _ = Account.objects.get_or_create(name=account_name)
        self.instance.account = account
        self.instance.engineer = self.cleaned_data.get("engineer")
        priority_value = self.cleaned_data.get("priority") or Request.Priority.MEDIUM
        self.instance.priority = priority_value
        request_date = self.cleaned_data.get("needed_by")
        if request_date:
            self.instance.start_date = request_date
        deployment_start = self.cleaned_data.get("deployment_start")
        deployment_end = self.cleaned_data.get("deployment_end")
        if deployment_start:
            self.instance.start_date = deployment_start
        if deployment_end:
            self.instance.due_date = deployment_end
        elif self.cleaned_data.get("engagement_type") != Request.Engagement.DEPLOYMENT:
            self.instance.due_date = None
        if "backup_engineer" in self.cleaned_data:
            self.instance.backup_engineer = self.cleaned_data.get("backup_engineer")
        return super().save(commit=commit)


class RequestAdminForm(forms.ModelForm):
    request_date = forms.DateField(
        label="Request Date",
        required=True,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        help_text="Date selected by the requestor; SLA and due date will align to this date.",
    )
    requestor = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=User.REQUEST_CREATOR_ROLES),
        required=True,
        widget=AvatarSelect(attrs={"class": "form-select", "data-avatar-select": "true"}),
        label="Requestor",
        help_text="Switch the request owner (Requestor/Requestor-ESS/PM-ESS).",
    )
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
            "request_date",
            "requestor",
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
        allow_capacity_override = kwargs.pop("allow_capacity_override", False)
        super().__init__(*args, **kwargs)
        # Flag used by Request.clean() to bypass engineer capacity validation when admin overrides.
        self.instance._allow_capacity_override = allow_capacity_override
        # Request date initial
        if self.instance and getattr(self.instance, "start_date", None):
            self.fields["request_date"].initial = self.instance.start_date
        # Requestor field setup
        self.fields["requestor"].queryset = self.fields["requestor"].queryset.order_by("first_name", "last_name")
        req_widget = self.fields["requestor"].widget
        if isinstance(req_widget, AvatarSelect):
            req_widget.avatar_mapping = _build_avatar_mapping(self.fields["requestor"].queryset)
        self.fields["requestor"].label_from_instance = _user_display
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

    def save(self, commit=True):
        self.instance.start_date = self.cleaned_data.get("request_date") or self.instance.start_date
        return super().save(commit=commit)


class RequestStatusForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ["status", "end_date"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select form-select-sm"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control form-control-sm"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance._allow_capacity_override = True

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


class EngineerActivityLogForm(forms.ModelForm):
    activity_type = forms.ChoiceField(
        label="Type of Activity",
        choices=EngineerActivityLog.ActivityType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    is_billable = forms.TypedChoiceField(
        label="Billable",
        choices=(
            ("true", "Billable"),
            ("false", "Not billable"),
        ),
        initial="true",
        coerce=lambda value: str(value).lower() in {"true", "1", "yes"},
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = EngineerActivityLog
        fields = [
            "request_date",
            "request",
            "account",
            "activity_type",
            "actual_hours",
            "details",
            "location",
            "is_billable",
            "status",
        ]
        labels = {
            "request_date": "Date of Activity",
            "request": "Related Request",
            "account": "Account",
            "actual_hours": "Actual Hours",
            "details": "Details",
            "location": "Work Location",
            "status": "Status",
        }
        widgets = {
            "request_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "request": forms.Select(attrs={"class": "form-select"}),
            "account": forms.Select(attrs={"class": "form-select"}),
            "actual_hours": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.25"}),
            "details": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, engineer=None, **kwargs):
        self.engineer = engineer
        if self.engineer is None:
            raise ValueError("EngineerActivityLogForm requires an engineer instance.")
        super().__init__(*args, **kwargs)

        account_field = self.fields["account"]
        account_field.required = False
        account_field.queryset = Account.objects.order_by("name")

        request_field = self.fields["request"]
        request_field.required = False
        related_requests = Request.objects.filter(
            Q(engineer=self.engineer) | Q(backup_engineer=self.engineer)
        ).order_by("-created_at").select_related("account")
        request_field.queryset = related_requests
        request_field.empty_label = "Select request (optional)"
        self.fields["is_billable"].initial = "true"

        request_date_field = self.fields["request_date"]
        request_date_field.required = True
        if not self.is_bound and not self.instance.pk:
            request_date_field.initial = timezone.now().date()

        if not self.is_bound:
            if self.instance.pk:
                self.fields["is_billable"].initial = "true" if self.instance.is_billable else "false"
                self.fields["activity_type"].initial = self.instance.activity_type
            else:
                self.fields["is_billable"].initial = "true"
                self.fields["activity_type"].initial = EngineerActivityLog.ActivityType.INTERNAL_SUPPORT
        else:
            raw_billable = self.data.get(self.add_prefix("is_billable"))
            if raw_billable is None:
                self.fields["is_billable"].initial = "true"

        if self.is_bound and self.errors:
            for name, field in self.fields.items():
                if name in self.errors:
                    widget = field.widget
                    css = widget.attrs.get("class", "")
                    if "is-invalid" not in css.split():
                        widget.attrs["class"] = (css + " is-invalid").strip()

    def clean_details(self):
        value = (self.cleaned_data.get("details") or "").strip()
        if not value:
            raise forms.ValidationError("Provide the activity details.")
        return value

    def clean_actual_hours(self):
        value = self.cleaned_data.get("actual_hours")
        if value is None:
            return value
        if value <= 0:
            raise forms.ValidationError("Actual hours must be greater than zero.")
        return value

    def clean_request(self):
        request_obj = self.cleaned_data.get("request")
        if not request_obj:
            return request_obj
        allowed_ids = set(self.fields["request"].queryset.values_list("id", flat=True))
        if request_obj.pk not in allowed_ids:
            raise forms.ValidationError("Select a request assigned to you.")
        return request_obj

    def clean(self):
        cleaned_data = super().clean()
        request_obj = cleaned_data.get("request")
        account = cleaned_data.get("account")
        if request_obj:
            if account and account != request_obj.account:
                self.add_error("account", "Account does not match the selected request.")
            else:
                cleaned_data["account"] = request_obj.account
        if not cleaned_data.get("account"):
            self.add_error("account", "Select an account or choose a request.")
        return cleaned_data


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