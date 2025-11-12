from django.contrib.auth.hashers import make_password
from django.db import migrations


def add_primary_account_manager(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.update_or_create(
        username="account_admin",
        defaults={
            "role": "requestor",
            "first_name": "Admin",
            "last_name": "Account Manager",
            "email": "account_admin@example.com",
            "password": make_password("Admin"),
            "is_active": True,
        },
    )


def remove_primary_account_manager(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(username="account_admin").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_add_role_demo_users"),
    ]

    operations = [
        migrations.RunPython(add_primary_account_manager, remove_primary_account_manager),
    ]
