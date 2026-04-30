from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0027_rename_hub_request_request__b23575_idx_hub_request_request_4c5451_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sqrsubmission",
            name="discount_rate",
            field=models.PositiveSmallIntegerField(
                choices=[(0, "No Discount"), (5, "5%"), (10, "10%"), (15, "15%")],
                default=0,
            ),
        ),
    ]
