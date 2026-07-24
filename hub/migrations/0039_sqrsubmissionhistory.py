from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("hub", "0038_sqrsubmissionchange"),
    ]

    operations = [
        migrations.CreateModel(
            name="SqrSubmissionHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[("updated", "Updated"), ("restored", "Restored")],
                        default="updated",
                        max_length=40,
                    ),
                ),
                ("field", models.CharField(blank=True, max_length=100)),
                ("old_values", models.JSONField(blank=True, default=dict)),
                ("new_values", models.JSONField(blank=True, default=dict)),
                ("summary", models.TextField(blank=True)),
                ("source", models.CharField(blank=True, max_length=120)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("restored_at", models.DateTimeField(blank=True, null=True)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sqr_history_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "restored_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sqr_history_restores",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history_entries",
                        to="hub.sqrsubmission",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-pk"],
                "indexes": [
                    models.Index(fields=["submission", "-created_at"], name="hub_sqrhist_submiss_9d3a4d_idx"),
                    models.Index(fields=["actor", "-created_at"], name="hub_sqrhist_actor_i_75f42a_idx"),
                    models.Index(fields=["action", "-created_at"], name="hub_sqrhist_action__3528de_idx"),
                ],
            },
        ),
    ]
