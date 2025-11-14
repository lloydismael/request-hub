from django.contrib.auth.hashers import make_password
from django.db import migrations

ENGINEERS = [
    ("Airoll Ross M. Santos", "AirollS@phildata.com"),
    ("Aldwin B. Banta", "AldwinB@phildata.com"),
    ("Archie Gerard U. Arengo", "ArchieA@phildata.com"),
    ("Christian Noel Claveria", "ChristianOC@phildata.com"),
    ("Errolyn S. Encontro", "ErrolynE@phildata.com"),
    ("Ferdinand D. Geli", "FerdinandG@phildata.com"),
    ("Francis Buensalida", "FrancisB@phildata.com"),
    ("Jeram C. Zamora", "JeramC@phildata.com"),
    ("Jhed Arevyne Pabanelas", "JhedAP@phildata.com"),
    ("John Paulo T. Barron", "PauloTB@phildata.com"),
    ("Lloyd Christian M. Ismael", "LloydI@phildata.com"),
    ("Marfelie B. Barcenas", "MarfelieB@phildata.com"),
    ("Marvin D. Garcia", "VinG@phildata.com"),
    ("Paul Gerald D. Buli", "GeraldDB@phildata.com"),
    ("Princess Nicole D. Nacianceno", "PrincessDN@phildata.com"),
    ("Royce Geronimo G. Cuizon", "RoyceGC@phildata.com"),
    ("Ryan Jay C. Mopal", "RyanCM@phildata.com"),
    ("William H. Tuazon", "WilliamT@phildata.com"),
]


def slug_username(name: str) -> str:
    import re

    username = re.sub(r"[^a-z0-9]", "", name.lower())
    return username[:20] or "user"


def split_name(name: str):
    parts = name.split()
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
    for full_name, corporate_email in ENGINEERS:
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
            user.role = "engineer"
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
                role="engineer",
                first_name=first,
                last_name=last,
                email=email_value,
                password=password_value,
                profile_completed=False,
            )


def set_engineer_contacts(apps, schema_editor):
    apply_roster(apps, schema_editor, use_phildata_emails=True)


def revert_engineer_contacts(apps, schema_editor):
    apply_roster(apps, schema_editor, use_phildata_emails=False)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_add_admin1_role_users"),
    ]

    operations = [
        migrations.RunPython(set_engineer_contacts, revert_engineer_contacts),
    ]
