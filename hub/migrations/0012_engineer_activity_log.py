from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0011_notification_actor_source"),
    ]

    operations = [
        migrations.CreateModel(
            name="EngineerActivityLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_date", models.DateField()),
                ("activity_type", models.CharField(max_length=120)),
                ("actual_hours", models.DecimalField(decimal_places=2, max_digits=5, validators=[MinValueValidator(0)])),
                ("details", models.TextField()),
                ("location", models.CharField(choices=[("wfa", "WFA"), ("office", "Office")], max_length=20)),
                ("is_billable", models.BooleanField(default=True)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("in_progress", "In Progress"), ("completed", "Completed")], default="in_progress", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="activity_logs", to="hub.account")),
                ("engineer", models.ForeignKey(limit_choices_to={"role": "engineer"}, on_delete=django.db.models.deletion.CASCADE, related_name="activity_logs", to=settings.AUTH_USER_MODEL)),
                ("request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="activity_logs", to="hub.request")),
            ],
            options={
                "ordering": ["-request_date", "-created_at"],
            },
        ),
    ]
