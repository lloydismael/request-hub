from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_role_demo_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    demo_users = [
        {
            "username": "engineer_admin",
            "role": "engineer",
            "first_name": "Engineer",
            "last_name": "Demo",
            "email": "engineer_admin@example.com",
        },
        {
            "username": "manager_admin",
            "role": "requestor",
            "first_name": "Account",
            "last_name": "Manager",
            "email": "manager_admin@example.com",
        },
    ]

    for entry in demo_users:
        User.objects.update_or_create(
            username=entry["username"],
            defaults={
                "role": entry["role"],
                "first_name": entry["first_name"],
                "last_name": entry["last_name"],
                "email": entry["email"],
                "password": make_password("Admin"),
                "is_active": True,
            },
        )


def remove_role_demo_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    usernames = ["engineer_admin", "manager_admin"]
    User.objects.filter(username__in=usernames).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_seed_default_users"),
    ]

    operations = [
        migrations.RunPython(create_role_demo_users, remove_role_demo_users),
    ]
