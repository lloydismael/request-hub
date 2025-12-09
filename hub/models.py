from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
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
        limit_choices_to={"role": "requestor"},
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
        limit_choices_to={"role": "engineer"},
    )
    backup_engineer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="backup_requests_assigned",
        blank=True,
        null=True,
        limit_choices_to={"role": "engineer"},
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ONGOING)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("hub:request-detail", args=[self.pk])

    def clean(self):
        super().clean()
        if self.engineer and self.status == self.Status.ONGOING:
            assigned = Request.objects.filter(
                engineer=self.engineer,
                status=self.Status.ONGOING,
            )
            if self.pk:
                assigned = assigned.exclude(pk=self.pk)
            if assigned.count() >= 5:
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
        self.full_clean()
        super().save(*args, **kwargs)
        if creating and not self.reference_code:
            self.reference_code = f"REQ-{self.pk:05d}"
            Request.objects.filter(pk=self.pk).update(reference_code=self.reference_code)

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
        """Return full working days since creation, counting only 24-hour intervals in Manila time."""
        created_dt = timezone.localtime(self.created_at, MANILA_TZ)
        if self.end_date:
            end_dt = datetime.combine(self.end_date, time(23, 59, 59, tzinfo=MANILA_TZ))
        else:
            end_dt = timezone.now().astimezone(MANILA_TZ)

        if end_dt <= created_dt:
            return 0

        total_seconds = (end_dt - created_dt).total_seconds()
        full_days = int(total_seconds // 86400)
        if full_days <= 0:
            return 0

        working_days = 0
        for offset in range(1, full_days + 1):
            current_day = (created_dt + timedelta(days=offset)).date()
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
            if days >= 5:
                return "red"
            if days > 3:
                return "amber"
            return "green"

        if priority == self.Priority.MEDIUM:
            if days >= 10:
                return "red"
            if days > 5:
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
            return days > 4
        return days > 5

    def __str__(self) -> str:
        return f"{self.reference_code or 'Request'} - {self.account.name}"


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
    def icon_class(self) -> str:
        message_lower = (self.message or "").lower()
        source_lower = (self.source or "").lower()
        if "new request" in source_lower or "new request" in message_lower:
            return "bi-plus-circle"
        if "assigned to request" in message_lower:
            return "bi-person-check"
        if "posted an update" in message_lower:
            return "bi-chat-left-text"
        if "completed" in message_lower or "closed" in message_lower:
            return "bi-clipboard-check"
        return "bi-bell"


class StatusLog(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="status_logs")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="status_logs")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.request.reference_code or 'Request'}: {self.author.get_full_name() or self.author.username}"
