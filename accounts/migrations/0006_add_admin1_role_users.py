from django.contrib.auth.hashers import make_password
from django.db import migrations


def add_admin1_role_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    entries = [
        {
            "username": "engineer_admin1",
            "role": "engineer",
            "first_name": "Engineer",
            "last_name": "Admin1",
            "email": "engineer_admin1@example.com",
        },
        {
            "username": "manager_admin1",
            "role": "requestor",
            "first_name": "Account",
            "last_name": "Manager",
            "email": "manager_admin1@example.com",
        },
    ]
    for entry in entries:
        User.objects.update_or_create(
            username=entry["username"],
            defaults={
                "role": entry["role"],
                "first_name": entry["first_name"],
                "last_name": entry["last_name"],
                "email": entry["email"],
                "password": make_password("Admin1"),
                "is_active": True,
            },
        )


def remove_admin1_role_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    usernames = ["engineer_admin1", "manager_admin1"]
    User.objects.filter(username__in=usernames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_add_secondary_admin"),
    ]

    operations = [
        migrations.RunPython(add_admin1_role_users, remove_admin1_role_users),
    ]
