from datetime import datetime, time, timedelta
from decimal import Decimal
from urllib.parse import quote
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

MANILA_TZ = ZoneInfo("Asia/Manila")

class Account(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Request(models.Model):
    class Priority(models.TextChoices):
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class Engagement(models.TextChoices):
        OPPORTUNITY = "opportunity", "Opportunity"
        TRAINING = "training", "Training"
        SUPPORT = "support", "Support"
        INQUIRY = "inquiry", "Inquiry"
        DEPLOYMENT = "deployment", "Deployment"
        PROJECT_MANAGEMENT = "project_management", "Project Management"
        CERTIFICATION = "certification", "Certification"

    class Status(models.TextChoices):
        ONGOING = "ongoing", "Ongoing"
        COMPLETED = "completed", "Completed"

    SLA_DAYS = {
        Priority.MEDIUM: 5,
        Priority.HIGH: 3,
    }

    reference_code = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    requestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requests_made",
        limit_choices_to={"role__in": ["requestor", "requestor_ess", "pm_ess", "pm_esg"]},
    )
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="requests")
    account_manager = models.CharField(max_length=255)
    product_category = models.CharField(
        max_length=50,
        choices=[
            ("Azure", "Azure"),
            ("M365", "M365"),
            ("VMware", "VMware"),
            ("Omnissa", "Omnissa"),
            ("Hybrid", "Hybrid"),
            ("Dell", "Dell"),
            ("HP", "HP"),
            ("Network", "Network"),
            ("Veeam", "Veeam"),
            ("Others", "Others"),
        ],
    )
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    engagement_type = models.CharField(max_length=20, choices=Engagement.choices)
    start_date = models.DateField(auto_now_add=True)
    due_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requests_assigned",
        blank=True,
        null=True,
        limit_choices_to={"role__in": ["engineer", "on_hold", "pm_esg"]},
    )
    backup_engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="backup_requests_assigned",
        blank=True,
        null=True,
        limit_choices_to={"role__in": ["engineer", "on_hold"]},
    )
    teams_chat_topic = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ONGOING)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class _ActiveManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(is_deleted=False)

    objects = _ActiveManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("hub:request-manage-collab", args=[self.pk])

    def clean(self):
        super().clean()
        bypass_capacity = getattr(self, "_allow_capacity_override", False)

        if self.engineer and self.status == self.Status.ONGOING and not bypass_capacity:
            assigned = Request.objects.filter(
                engineer=self.engineer,
                status=self.Status.ONGOING,
            )
            if self.pk:
                assigned = assigned.exclude(pk=self.pk)

            # Capacity: default 5 ongoing; when an engineer already has an ongoing deployment/certification, cap at 3.
            # This still allows assigning the first deployment even if they already carry up to 4 non-deployment requests.
            has_ongoing_deployment = assigned.filter(engagement_type__in=[
                self.Engagement.DEPLOYMENT, self.Engagement.CERTIFICATION
            ]).exists()
            max_allowed = 3 if has_ongoing_deployment else 5

            current_load = assigned.count()
            if current_load >= max_allowed:
                if max_allowed == 3:
                    raise ValidationError(
                        {
                            "engineer": (
                                "Selected engineer is at the deployment capacity (max 3 ongoing while a deployment is active). "
                                "Choose another engineer or wait until a deployment is completed."
                            )
                        }
                    )
                raise ValidationError({"engineer": "Selected engineer already has 5 ongoing requests."})
        if self.end_date and self.status != self.Status.COMPLETED:
            raise ValidationError({"end_date": "Mark the request as completed before setting an end date."})
        if self.status == self.Status.COMPLETED and not self.end_date:
            self.end_date = timezone.now().date()

    def save(self, *args, **kwargs):
        creating = self.pk is None
        if creating and not self.start_date:
            self.start_date = timezone.now().date()
        if self.due_date is None:
            computed_due = self.compute_due_date()
            if computed_due:
                self.due_date = computed_due
        if not self.teams_chat_topic:
            self.teams_chat_topic = self._build_teams_chat_topic(reference_code=self.reference_code)
        self.full_clean(exclude=["requestor"])
        super().save(*args, **kwargs)
        if creating and not self.reference_code:
            self.reference_code = f"REQ-{self.pk:05d}"
            update_payload = {"reference_code": self.reference_code}
            topic = self._build_teams_chat_topic(reference_code=self.reference_code)
            if topic != self.teams_chat_topic:
                self.teams_chat_topic = topic
                update_payload["teams_chat_topic"] = topic
            Request.objects.filter(pk=self.pk).update(**update_payload)
        elif creating:
            updated_topic = self._build_teams_chat_topic(reference_code=self.reference_code)
            if updated_topic != self.teams_chat_topic:
                self.teams_chat_topic = updated_topic
                Request.objects.filter(pk=self.pk).update(teams_chat_topic=updated_topic)
        else:
            updated_topic = self._build_teams_chat_topic(reference_code=self.reference_code)
            if updated_topic and updated_topic != self.teams_chat_topic:
                self.teams_chat_topic = updated_topic
                Request.objects.filter(pk=self.pk).update(teams_chat_topic=updated_topic)

    @property
    def is_overdue(self) -> bool:
        if self.status == self.Status.COMPLETED or not self.due_date:
            return False
        return timezone.now().date() > self.due_date

    def compute_due_date(self):
        sla_days = self.SLA_DAYS.get(self.priority)
        if sla_days is None:
            return None
        base_date = self.start_date or timezone.now().date()
        days_remaining = sla_days
        candidate = base_date
        while days_remaining > 0:
            candidate += timedelta(days=1)
            if candidate.weekday() < 5:  # Monday-Friday are working days
                days_remaining -= 1
        return candidate

    @property
    def days_since_creation(self) -> int:
        """Return working days since the requested start date (Request Date), not creation time."""
        start_date = self.start_date or timezone.localtime(self.created_at, MANILA_TZ).date()
        start_dt = datetime.combine(start_date, time(0, 0, tzinfo=MANILA_TZ))
        if self.end_date:
            end_dt = datetime.combine(self.end_date, time(23, 59, 59, tzinfo=MANILA_TZ))
        else:
            end_dt = timezone.now().astimezone(MANILA_TZ)

        if end_dt <= start_dt:
            return 0

        total_seconds = (end_dt - start_dt).total_seconds()
        full_days = int(total_seconds // 86400)
        if full_days <= 0:
            return 0

        working_days = 0
        for offset in range(1, full_days + 1):
            current_day = (start_dt + timedelta(days=offset)).date()
            if current_day.weekday() < 5:  # Monday=0, Sunday=6
                working_days += 1
        return working_days

    @property
    def sla_threshold_days(self) -> int | None:
        return self.SLA_DAYS.get(self.priority)

    @property
    def sla_overrun(self) -> bool:
        threshold = self.sla_threshold_days
        if threshold is None:
            return False
        if self.status == self.Status.COMPLETED:
            return self.missed_sla
        if self.status != self.Status.ONGOING:
            return False
        return self.days_since_creation > threshold

    @property
    def missed_sla(self) -> bool:
        """Return True when the completion date exceeds the computed SLA target."""
        if not self.end_date or not self.due_date:
            return False
        return self.end_date > self.due_date

    @property
    def admin_days_rag(self) -> str:
        """Return the RAG (red/amber/green) state for the admin days badge."""
        days = self.days_since_creation
        priority = self.priority

        if priority == self.Priority.HIGH:
            if days > 3:
                return "red"
            if days >= 2:
                return "amber"
            return "green"

        if priority == self.Priority.MEDIUM:
            if days > 5:
                return "red"
            if days >= 4:
                return "amber"
            return "green"

        return "neutral"

    @property
    def admin_days_badge_classes(self) -> str:
        """Return Bootstrap classes for the admin days badge based on the RAG state."""
        mapping = {
            "green": "bg-success-subtle text-success border border-success-subtle",
            "amber": "bg-warning-subtle text-warning border border-warning-subtle",
            "red": "bg-danger text-white",
        }
        return mapping.get(self.admin_days_rag, "bg-light text-dark border")

    @property
    def admin_days_overdue(self) -> bool:
        if self.status != self.Status.ONGOING:
            return False
        days = self.days_since_creation
        if self.priority == self.Priority.HIGH:
            return days > 3
        return days > 5

    @property
    def teams_chat_url(self) -> str:
        engineer_email = (
            self.engineer.email if self.engineer and self.engineer.email else None
        )
        manager_email = (
            self.requestor.email if self.requestor and self.requestor.email else None
        )
        backup_email = (
            self.backup_engineer.email
            if self.backup_engineer and self.backup_engineer.email
            else None
        )
        if not engineer_email or not manager_email:
            return ""
        participant_set = {engineer_email, manager_email, "JeanM@phildata.com"}
        if backup_email:
            participant_set.add(backup_email)
        participants = ",".join(sorted(email for email in participant_set if email))
        topic = self.teams_chat_topic or self._build_teams_chat_topic(reference_code=self.reference_code)
        engineer_display = (
            self.engineer.get_full_name()
            if self.engineer and self.engineer.get_full_name()
            else (self.engineer.username if self.engineer and self.engineer.username else "our support engineering team")
        )
        message = (
            f"I'm {engineer_display}, and I've been assigned as the engineer to handle your request. "
            "I'll be working closely with you to ensure everything is addressed promptly and accurately.\n\n"
            "If you have any additional details or questions regarding your request, please feel free to share it with me. "
            "I'll keep you updated on the progress and next steps.\n\n"
            "Looking forward to assisting you!"
        )
        return (
            "https://teams.microsoft.com/l/chat/0/0?users="
            f"{quote(participants)}&topicName={quote(topic)}&message={quote(message)}"
        )

    def __str__(self) -> str:
        return f"{self.reference_code or 'Request'} - {self.account.name}"

    def _build_teams_chat_topic(self, reference_code: str | None = None) -> str:
        reference = reference_code or self.reference_code or "Request"
        account_name = self.account.name if self.account else ""
        if account_name:
            return f"{reference} · {account_name}"
        return reference


class RequestCommunication(models.Model):
    class Channel(models.TextChoices):
        OUTLOOK = "outlook", "Outlook"
        TEAMS = "teams", "Teams"

    request = models.ForeignKey(
        "Request",
        on_delete=models.CASCADE,
        related_name="communications",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="request_communications",
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["request", "user", "channel"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_channel_display()} · {self.request.reference_code or 'Request'}"


class EngineerActivityLog(models.Model):
    class Location(models.TextChoices):
        WFA = "wfa", "WFA"
        OFFICE = "office", "Office"
        ONSITE = "onsite", "Onsite"

    class ActivityType(models.TextChoices):
        LEARNING = "learning", "Learning"
        INTERNAL_SUPPORT = "internal_support", "Internal Support"
        ON_CALL_SUPPORT = "on_call_support", "On-Call Support"
        PRE_SALES = "pre_sales", "Pre-Sales"
        PROJECT_MANAGEMENT = "project_management", "Project Management"
        TRAINING = "training", "Training"
        DEPLOYMENT = "deployment", "Deployment"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity_logs",
        limit_choices_to={"role": "engineer"},
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="activity_logs",
    )
    request = models.ForeignKey(
        "Request",
        on_delete=models.SET_NULL,
        related_name="activity_logs",
        blank=True,
        null=True,
    )
    request_date = models.DateField()
    activity_type = models.CharField(
        max_length=40,
        choices=ActivityType.choices,
        default=ActivityType.INTERNAL_SUPPORT,
    )
    actual_hours = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    details = models.TextField()
    location = models.CharField(max_length=20, choices=Location.choices)
    is_billable = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-request_date", "-created_at"]

    def __str__(self) -> str:
        engineer_name = self.engineer.get_full_name() or self.engineer.username or "Engineer"
        return f"{engineer_name} · {self.activity_type} · {self.request_date:%Y-%m-%d}"


class SqrSubmission(models.Model):
    class Status(models.TextChoices):
        FOR_PROCESSING = "submitted", "For Processing"
        FOR_REVISION = "for_revision", "For Revision"
        APPROVED = "reviewed", "Approved"

    class ProposalStatus(models.TextChoices):
        SUBMITTED_PENDING = "submitted_pending", "Submitted \u2013 Pending"
        NEGOTIATION_REVIEW = "negotiation_review", "Negotiation / Review"
        CLOSED_WON = "closed_won", "Closed Won"
        CLOSED_LOST = "closed_lost", "Closed Lost"

    class DeliveryHealth(models.TextChoices):
        ON_TRACK = "on_track", "On Track"
        OFF_TRACK = "off_track", "Off Track"
        AT_RISK = "at_risk", "At Risk"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class OverallStatus(models.TextChoices):
        ON_HOLD = "on_hold", "On Hold"
        PLANNING = "planning", "Planning"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class RevenueStatus(models.TextChoices):
        INVOICED = "invoiced", "Invoiced"
        PARTIAL = "partial", "Partial"
        PENDING = "pending", "Pending"

    reference_code = models.CharField(max_length=24, unique=True, editable=False, blank=True, null=True)
    year = models.PositiveIntegerField(editable=False, db_index=True)
    sequence_number = models.PositiveIntegerField(editable=False, db_index=True, blank=True, null=True)
    linked_request = models.ForeignKey(
        "Request",
        on_delete=models.SET_NULL,
        related_name="sqr_links",
        blank=True,
        null=True,
        verbose_name="RQ ID",
    )
    engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sqr_submissions",
        limit_choices_to={"role": "engineer"},
    )
    pm_esg_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sqr_reviews_assigned",
        limit_choices_to={"role": "pm_esg"},
    )
    customer_name = models.CharField(max_length=255)
    customer_company = models.CharField(max_length=255, blank=True)
    customer_contact = models.CharField(max_length=255, blank=True)
    project_title = models.CharField(max_length=255)
    project_details = models.TextField()
    sse_manhrs = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True)
    documentation_links = models.TextField(help_text="One link per line.")
    sqr_folder_link = models.URLField(blank=True)
    remarks = models.TextField(blank=True)
    quotation_total_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )
    discount_rate = models.PositiveSmallIntegerField(
        choices=[
            (0, "No Discount"),
            (5, "5%"),
            (10, "10%"),
            (15, "15%"),
        ],
        default=0,
    )
    pm_manhrs = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True
    )
    hourly_rate = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True,
        help_text="Rate per manhour (PHP).",
    )
    # Proposal Stage – cost breakdown columns (M, O, P in Excel)
    sse_amount = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True,
        help_text="SSE labour cost (PHP).",
    )
    pm_amount = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True,
        help_text="PM labour cost (PHP).",
    )
    managed_support_amount = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True,
        help_text="Managed Support Service amount (PHP).",
    )
    validity_due_date = models.DateField(blank=True, null=True)
    po_attachment_link = models.URLField(blank=True)
    po_attached_at = models.DateTimeField(blank=True, null=True)
    revenue_overview = models.TextField(blank=True)
    # Proposal Stage – deal tracking (set by PM after internal approval)
    proposal_status = models.CharField(
        max_length=25, choices=ProposalStatus.choices, blank=True, default=""
    )
    # Service Delivery Stage – visible when proposal_status == CLOSED_WON
    delivery_health = models.CharField(
        max_length=20, choices=DeliveryHealth.choices, blank=True, default=""
    )
    delivery_progress = models.PositiveSmallIntegerField(blank=True, null=True)
    delivery_start_date = models.DateField(blank=True, null=True)
    delivery_target_finish_date = models.DateField(blank=True, null=True)
    delivery_actual_finish_date = models.DateField(blank=True, null=True)
    delivery_completion_signed_date = models.DateField(blank=True, null=True)
    # Service Delivery Stage – extra columns (X–AK in Excel)
    po_pnl_date = models.DateField(blank=True, null=True, verbose_name="PO/PNL Date")
    assigned_pm = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sqr_assigned_pm",
        blank=True,
        null=True,
        verbose_name="Assigned PM",
    )
    assigned_sse = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sqr_assigned_sse",
        blank=True,
        null=True,
        verbose_name="Assigned SSE",
    )
    overall_status = models.CharField(
        max_length=20, choices=OverallStatus.choices, blank=True, default=""
    )
    key_updates_risks = models.TextField(blank=True)
    warranty_end_date = models.DateField(blank=True, null=True, verbose_name="Post-service Warranty End Date")
    managed_support_start_date = models.DateField(blank=True, null=True)
    managed_support_end_date = models.DateField(blank=True, null=True)
    # Revenue Stage – columns (AL–AP in Excel)
    revenue_date = models.DateField(blank=True, null=True, verbose_name="SI/Revenue Date")
    revenue_source = models.CharField(max_length=100, blank=True)
    revenue_reference_no = models.CharField(max_length=100, blank=True)
    revenue_status = models.CharField(
        max_length=20, choices=RevenueStatus.choices, blank=True, default=""
    )
    revenue_remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.FOR_PROCESSING)
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sqr_reviews_completed",
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    revenue_unlocked = models.BooleanField(
        default=False,
        help_text="Set to True when PM clicks 'To Revenue' in Step 3 to enable Step 4.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.reference_code or f"SQR draft #{self.pk}"

    @property
    def documentation_link_list(self) -> list[str]:
        links = []
        for raw in (self.documentation_links or "").splitlines():
            cleaned = raw.strip()
            if cleaned:
                links.append(cleaned)
        return links

    @property
    def discounted_price(self):
        if self.quotation_total_price is None:
            return None
        discount = Decimal(self.discount_rate or 0) / Decimal("100")
        discounted = self.quotation_total_price * (Decimal("1") - discount)
        return discounted.quantize(Decimal("0.01"))

    @property
    def base_cost(self):
        """Computed cost = (sse_manhrs + pm_manhrs) × hourly_rate."""
        if not self.hourly_rate:
            return None
        total_hrs = (self.sse_manhrs or Decimal("0")) + (self.pm_manhrs or Decimal("0"))
        if not total_hrs:
            return None
        return (total_hrs * self.hourly_rate).quantize(Decimal("0.01"))

    @property
    def base_cost_discounted(self):
        """Computed cost after applying discount_rate."""
        base = self.base_cost
        if base is None:
            return None
        discount = Decimal(self.discount_rate or 0) / Decimal("100")
        return (base * (Decimal("1") - discount)).quantize(Decimal("0.01"))

    @property
    def computed_gross_total(self):
        """SSE Amount + PM Amount + Managed Support Amount."""
        sse = self.sse_amount or Decimal("0")
        pm = self.pm_amount or Decimal("0")
        mgmt = self.managed_support_amount or Decimal("0")
        gross = sse + pm + mgmt
        return gross.quantize(Decimal("0.01")) if gross else None

    @property
    def computed_discount_amount(self):
        """Gross total × discount_rate / 100."""
        gross = self.computed_gross_total
        if gross is None:
            return None
        return (gross * Decimal(self.discount_rate or 0) / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def computed_total_price(self):
        """Gross total after applying discount."""
        gross = self.computed_gross_total
        if gross is None:
            return None
        discount = Decimal(self.discount_rate or 0) / Decimal("100")
        return (gross * (Decimal("1") - discount)).quantize(Decimal("0.01"))

    _IMPL_SCOPES = frozenset(["Implementation", "Implementation and Project Management"])
    _WARRANTY_SCOPES = frozenset([
        "Implementation",
        "Implementation and Project Management",
        "Managed Support and Maintenance Service",
    ])

    @property
    def computed_post_svc_warranty_end_date(self):
        """Completion Signed Date + 30 days — only for Implementation / Impl+PM scopes."""
        if self.project_details in self._IMPL_SCOPES and self.delivery_completion_signed_date:
            return self.delivery_completion_signed_date + timedelta(days=30)
        return None

    @property
    def computed_warranty_end_date(self):
        """Completion Signed Date + 30 days — for all warranty scopes (Impl / Impl+PM / Managed Support)."""
        if self.project_details in self._WARRANTY_SCOPES and self.delivery_completion_signed_date:
            return self.delivery_completion_signed_date + timedelta(days=30)
        return None

    @property
    def computed_managed_support_end_date(self):
        """Support Start Date (Col AJ) + 365 days.
        Only computed when managed_support_start_date is explicitly set;
        otherwise returns None (displayed as NA).
        """
        if self.managed_support_start_date:
            return self.managed_support_start_date + timedelta(days=365)
        return None

    @property
    def revenue_stage_key(self) -> str:
        if self.status == self.Status.APPROVED and self.po_attachment_link:
            return "revenue"
        if self.status == self.Status.APPROVED:
            return "order"
        return "quotation"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        if creating and not self.year:
            self.year = timezone.now().astimezone(MANILA_TZ).year

        # Auto-compute SSE Amount (col M = col L × 2000) and PM Amount (col O = col N × 3000)
        if self.sse_manhrs is not None:
            self.sse_amount = (Decimal(str(self.sse_manhrs)) * Decimal("2000")).quantize(Decimal("0.01"))
        else:
            self.sse_amount = None
        if self.pm_manhrs is not None:
            self.pm_amount = (Decimal(str(self.pm_manhrs)) * Decimal("3000")).quantize(Decimal("0.01"))
        else:
            self.pm_amount = None

        super().save(*args, **kwargs)

        if creating and not self.reference_code:
            last_in_year = (
                SqrSubmission.objects.filter(year=self.year)
                .exclude(pk=self.pk)
                .order_by("-sequence_number")
                .first()
            )
            next_number = (last_in_year.sequence_number if last_in_year and last_in_year.sequence_number else 0) + 1
            reference_code = f"SQR-{self.year}-{next_number:04d}"
            SqrSubmission.objects.filter(pk=self.pk).update(
                sequence_number=next_number,
                reference_code=reference_code,
            )
            self.sequence_number = next_number
            self.reference_code = reference_code


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    related_request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    actor = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.message

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=["is_read"])

    @property
    def category_key(self) -> str:
        message_lower = (self.message or "").lower()
        source_lower = (self.source or "").lower()
        if "nudge" in source_lower or "reminder" in message_lower:
            return "reminder"
        if "new request" in source_lower or "new request" in message_lower:
            return "new_request"
        if "assigned to request" in message_lower or "assignment" in source_lower:
            return "assignment"
        if "status update" in source_lower or "posted an update" in message_lower or " updated " in message_lower:
            return "update"
        if "completed" in message_lower or "closed" in message_lower or "close" in source_lower:
            return "completion"
        return "system"

    @property
    def category_label(self) -> str:
        labels = {
            "new_request": "New Request",
            "assignment": "Assignment",
            "update": "Status Update",
            "completion": "Completion",
            "reminder": "Reminder",
            "system": "System",
        }
        return labels.get(self.category_key, "System")

    @property
    def action_label(self) -> str:
        if not self.related_request:
            return "View"
        if self.category_key in {"update", "completion"}:
            return "Review Update"
        if self.category_key in {"new_request", "assignment", "reminder"}:
            return "Open Request"
        return "Manage"

    @property
    def icon_class(self) -> str:
        icons = {
            "new_request": "bi-plus-circle-fill",
            "assignment": "bi-person-workspace",
            "update": "bi-chat-left-text-fill",
            "completion": "bi-check2-circle",
            "reminder": "bi-alarm",
            "system": "bi-bell",
        }
        return icons.get(self.category_key, "bi-bell")


class StatusLog(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="status_logs")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="status_logs")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.request.reference_code or 'Request'}: {self.author.get_full_name() or self.author.username}"
