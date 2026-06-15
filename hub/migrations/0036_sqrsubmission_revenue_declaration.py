# Generated manually for SQR revenue declaration column

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0035_request_soft_delete"),
    ]

    operations = [
        migrations.AddField(
            model_name="sqrsubmission",
            name="revenue_declaration",
            field=models.CharField(
                blank=True,
                choices=[("declared", "Declared"), ("not_yet", "Not Yet")],
                default="",
                max_length=20,
            ),
        ),
    ]
