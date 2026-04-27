from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0021_alter_sqrsubmission_status_workflow"),
    ]

    operations = [
        migrations.AddField(
            model_name="sqrsubmission",
            name="discount_rate",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (5, "5%"),
                    (10, "10%"),
                    (15, "15%"),
                ],
                default=5,
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="po_attached_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="po_attachment_link",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="quotation_total_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=14,
                null=True,
                validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="revenue_overview",
            field=models.TextField(blank=True),
        ),
    ]
