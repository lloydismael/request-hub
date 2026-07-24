from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("hub", "0037_sqrsubmission_unique_linked_request"),
    ]

    operations = [
        migrations.CreateModel(
            name="SqrSubmissionChange",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("field", models.CharField(max_length=100)),
                ("old_values", models.JSONField()),
                ("new_values", models.JSONField()),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("undone_at", models.DateTimeField(blank=True, null=True)),
                (
                    "changed_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sqr_field_changes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="field_changes",
                        to="hub.sqrsubmission",
                    ),
                ),
                (
                    "undone_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sqr_field_changes_undone",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-changed_at"],
                "indexes": [
                    models.Index(fields=["submission", "field", "changed_at"], name="hub_sqrsubm_submiss_070ad9_idx"),
                    models.Index(fields=["undone_at"], name="hub_sqrsubm_undone__d1dfff_idx"),
                ],
            },
        ),
    ]
