from django.contrib.auth.hashers import make_password
from django.db import migrations

from hub.constants import ACCOUNT_MANAGER_NAMES, ENGINEER_NAMES


def slug_username(name: str) -> str:
    import re

    username = re.sub(r"[^a-z0-9]", "", name.lower())
    return username[:20] or "user"


def create_default_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")

    admin, _ = User.objects.get_or_create(
        username="Admin",
        defaults={
            "email": "admin@example.com",
            "role": "admin",
            "is_staff": True,
            "is_superuser": True,
            "first_name": "System",
            "last_name": "Administrator",
        },
    )
    admin.password = make_password("Admin")
    admin.save(update_fields=["password"])

    for name in ACCOUNT_MANAGER_NAMES:
        username = slug_username(name)
        first, *rest = name.split(" ")
        User.objects.update_or_create(
            username=username,
            defaults={
                "role": "requestor",
                "first_name": first,
                "last_name": " ".join(rest) or first,
                "email": f"{username}@example.com",
                "password": make_password("RequestHub123"),
            },
        )

    for name in ENGINEER_NAMES:
        username = slug_username(name)
        first, *rest = name.split(" ")
        User.objects.update_or_create(
            username=username,
            defaults={
                "role": "engineer",
                "first_name": first,
                "last_name": " ".join(rest) or first,
                "email": f"{username}@example.com",
                "password": make_password("RequestHub123"),
            },
        )


def remove_default_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    usernames = ["Admin"]
    usernames.extend(slug_username(name) for name in ACCOUNT_MANAGER_NAMES)
    usernames.extend(slug_username(name) for name in ENGINEER_NAMES)
    User.objects.filter(username__in=usernames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_users, remove_default_users),
    ]
