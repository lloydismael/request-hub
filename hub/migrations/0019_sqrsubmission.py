from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_add_pm_esg_role"),
        ("hub", "0018_request_add_project_management_engagement"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SqrSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference_code", models.CharField(blank=True, editable=False, max_length=24, null=True, unique=True)),
                ("year", models.PositiveIntegerField(db_index=True, editable=False)),
                ("sequence_number", models.PositiveIntegerField(blank=True, db_index=True, editable=False, null=True)),
                ("customer_name", models.CharField(max_length=255)),
                ("customer_company", models.CharField(blank=True, max_length=255)),
                ("customer_contact", models.CharField(blank=True, max_length=255)),
                ("project_title", models.CharField(max_length=255)),
                ("project_details", models.TextField()),
                ("documentation_links", models.TextField(help_text="One link per line.")),
                ("status", models.CharField(choices=[("submitted", "Submitted"), ("reviewed", "Reviewed")], default="submitted", max_length=20)),
                ("review_notes", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "engineer",
                    models.ForeignKey(
                        limit_choices_to={"role": "engineer"},
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sqr_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "pm_esg_reviewer",
                    models.ForeignKey(
                        limit_choices_to={"role": "pm_esg"},
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sqr_reviews_assigned",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sqr_reviews_completed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
