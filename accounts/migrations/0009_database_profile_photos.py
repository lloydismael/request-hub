from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import migrations, models

import accounts.models
import accounts.storage


def load_existing_profile_photos(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    storage = accounts.storage.DatabaseMediaStorage()
    media_root = getattr(settings, "MEDIA_ROOT", "")
    for user in User.objects.exclude(profile_photo=""):
        file_field = user.profile_photo
        name = getattr(file_field, "name", "")
        if not name:
            continue
        if storage.exists(name):
            continue
        candidate_paths = []
        if media_root:
            candidate_paths.append(Path(media_root) / name)
        candidate_paths.append(Path(name))
        for candidate in candidate_paths:
            if candidate.exists() and candidate.is_file():
                with candidate.open("rb") as src:
                    storage.save(name, ContentFile(src.read(), name=candidate.name))
                break


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_update_account_manager_contacts"),
    ]

    operations = [
        migrations.CreateModel(
            name="StoredFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("original_name", models.CharField(blank=True, max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=100)),
                ("size", models.PositiveIntegerField(default=0)),
                ("data", models.BinaryField(editable=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.AlterField(
            model_name="user",
            name="profile_photo",
            field=models.ImageField(
                blank=True,
                null=True,
                storage=accounts.storage.DatabaseMediaStorage(),
                upload_to=accounts.models.user_profile_photo_upload_to,
            ),
        ),
        migrations.RunPython(load_existing_profile_photos, noop_reverse),
    ]
