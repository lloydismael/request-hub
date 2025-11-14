from django.contrib.auth.hashers import make_password
from django.db import migrations

ACCOUNT_MANAGERS = [
    ("Aileen B. Gutierrez", "AileenG@phildata.com"),
    ("Anabelle D. Alapide", "AnabelleA@phildata.com"),
    ("Charisse P. Plata", "CharriseP@phildata.com"),
    ("Christine Joy A. Fabros", "ChristineF@phildata.com"),
    ("Elisha Jeimarie S. Tañada", "ElishaJ@phildata.com"),
    ("Jimlyn Espinosa", "JimlynE@phildata.com"),
    ("Kevin Dela Cruz", "KevinDC@phildata.com"),
    ("Kristel Camill V. Roldan", "KristelR@phildata.com"),
    ("Leonarda G. Lucena", "LeonardaL@phildata.com"),
    ("Manilyn Villaflores", "ManilynV@phildata.com"),
    ("Marvin I. San Miguel", "MarvinSM@phildata.com"),
    ("Mica Ella R. Labindao", "MicaL@phildata.com"),
    ("Orly N. Palomar, Jr.", "Orlyp@phildata.com"),
    ("Reennalyn F. Ortilano", "ReennalynO@phildata.com"),
    ("Rowell C. De Leon", "RowellDL@phildata.com"),
]


def slug_username(name: str) -> str:
    import re

    username = re.sub(r"[^a-z0-9]", "", name.lower())
    return username[:20] or "user"


def split_name(name: str):
    parts = name.replace(",", "").split()
    first = parts[0] if parts else ""
    last = " ".join(parts[1:]) if len(parts) > 1 else first
    return first, last


def _get_user(User, slug_username_value: str, email_username: str, corporate_email: str):
    return (
        User.objects.filter(username=email_username).first()
        or User.objects.filter(username=corporate_email).first()
        or User.objects.filter(username=slug_username_value).first()
        or User.objects.filter(email__iexact=corporate_email).first()
    )


def apply_roster(apps, schema_editor, *, use_phildata_emails: bool):
    User = apps.get_model("accounts", "User")
    for full_name, corporate_email in ACCOUNT_MANAGERS:
        first, last = split_name(full_name)
        slug_value = slug_username(full_name)
        email_username = corporate_email.lower()
        if use_phildata_emails:
            username_value = corporate_email
            email_value = corporate_email
            password_value = make_password("@Password")
        else:
            username_value = slug_value
            email_value = f"{slug_value}@example.com"
            password_value = make_password("RequestHub123")

        user = _get_user(User, slug_value, email_username, corporate_email)

        if user:
            user.username = username_value
            user.email = email_value
            user.first_name = first
            user.last_name = last
            user.role = "requestor"
            user.password = password_value
            user.profile_completed = False
            user.save(update_fields=[
                "username",
                "email",
                "first_name",
                "last_name",
                "role",
                "password",
                "profile_completed",
            ])
        else:
            User.objects.create(
                username=username_value,
                role="requestor",
                first_name=first,
                last_name=last,
                email=email_value,
                password=password_value,
                profile_completed=False,
            )


def set_account_manager_contacts(apps, schema_editor):
    apply_roster(apps, schema_editor, use_phildata_emails=True)


def revert_account_manager_contacts(apps, schema_editor):
    apply_roster(apps, schema_editor, use_phildata_emails=False)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_update_engineer_contacts"),
    ]

    operations = [
        migrations.RunPython(set_account_manager_contacts, revert_account_manager_contacts),
    ]
