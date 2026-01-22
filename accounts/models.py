from uuid import uuid4

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from .storage import DatabaseMediaStorage


def user_profile_photo_upload_to(instance, filename):
    suffix = ""
    if filename and "." in filename:
        suffix = f".{filename.rsplit('.', 1)[-1]}"
    return f"profile_photos/{uuid4().hex}{suffix}"


class StoredFile(models.Model):
    name = models.CharField(max_length=255, unique=True)
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(default=0)
    data = models.BinaryField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    class Roles(models.TextChoices):
        REQUESTOR = "requestor", "Requestor"
        REQUESTOR_ESS = "requestor_ess", "Requestor-ESS"
        PM_ESS = "pm_ess", "PM-ESS"
        ENGINEER = "engineer", "Engineer"
        ADMIN = "admin", "Admin"

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[RegexValidator(r"^[0-9+\-() ]*$", "Phone number contains invalid characters.")],
    )
    profile_photo = models.ImageField(
        upload_to=user_profile_photo_upload_to,
        storage=DatabaseMediaStorage(),
        blank=True,
        null=True,
    )
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.REQUESTOR)
    REQUESTOR_ROLES = (Roles.REQUESTOR, Roles.REQUESTOR_ESS)
    REQUEST_CREATOR_ROLES = (Roles.REQUESTOR, Roles.REQUESTOR_ESS, Roles.PM_ESS)
    profile_completed = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)

    def must_complete_profile(self) -> bool:
        required_fields = [self.email, self.phone_number, self.profile_photo]
        return not self.profile_completed or any(not value for value in required_fields)

    def mark_profile_complete(self):
        self.profile_completed = True
        self.save(update_fields=["profile_completed"])

    @property
    def profile_photo_url(self):
        if not self.profile_photo:
            return ""
        try:
            url = self.profile_photo.url
        except ValueError:
            return ""
        return url
