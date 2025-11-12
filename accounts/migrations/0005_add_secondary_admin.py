from django.contrib.auth.hashers import make_password
from django.db import migrations


def add_secondary_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.update_or_create(
        username="Admin1",
        defaults={
            "role": "admin",
            "first_name": "Secondary",
            "last_name": "Administrator",
            "email": "admin1@example.com",
            "password": make_password("Admin1"),
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        },
    )


def remove_secondary_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(username="Admin1").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_add_primary_account_manager"),
    ]

    operations = [
        migrations.RunPython(add_secondary_admin, remove_secondary_admin),
    ]
