import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Account",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Request",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference_code", models.CharField(blank=True, editable=False, max_length=20, unique=True)),
                ("account_manager", models.CharField(max_length=255)),
                (
                    "product_category",
                    models.CharField(
                        choices=[
                            ("Azure", "Azure"),
                            ("M365", "M365"),
                            ("VMware", "VMware"),
                            ("Omnissa", "Omnissa"),
                            ("Hybrid", "Hybrid"),
                            ("Others", "Others"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[("medium", "Medium"), ("high", "High")], default="medium", max_length=10
                    ),
                ),
                (
                    "engagement_type",
                    models.CharField(
                        choices=[
                            ("opportunity", "Opportunity"),
                            ("training", "Training"),
                            ("support", "Support"),
                            ("inquiry", "Inquiry"),
                        ],
                        max_length=20,
                    ),
                ),
                ("start_date", models.DateField(auto_now_add=True)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("ongoing", "Ongoing"), ("completed", "Completed")],
                        default="ongoing",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "account",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requests", to="hub.account"),
                ),
                (
                    "engineer",
                    models.ForeignKey(
                        blank=True,
                        limit_choices_to={"role": "engineer"},
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requests_assigned",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "requestor",
                    models.ForeignKey(
                        limit_choices_to={"role": "requestor"},
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requests_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_read", models.BooleanField(default=False)),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "related_request",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="hub.request",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
