from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0024_allow_pm_esg_requestor"),
    ]

    operations = [
        migrations.AddField(
            model_name="sqrsubmission",
            name="pm_manhrs",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=8,
                null=True,
                validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="hourly_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[MinValueValidator(0)],
                help_text="Rate per manhour (PHP).",
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="proposal_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("submitted_pending", "Submitted \u2013 Pending"),
                    ("negotiation_review", "Negotiation / Review"),
                    ("closed_won", "Closed Won"),
                    ("closed_lost", "Closed Lost"),
                ],
                default="",
                max_length=25,
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="delivery_health",
            field=models.CharField(
                blank=True,
                choices=[
                    ("on_track", "On Track"),
                    ("off_track", "Off Track"),
                    ("at_risk", "At Risk"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="delivery_progress",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="delivery_start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="delivery_target_finish_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="delivery_actual_finish_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="delivery_completion_signed_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
