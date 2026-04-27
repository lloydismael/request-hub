from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0020_sqrsubmission_add_sse_manhrs_and_remarks"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sqrsubmission",
            name="status",
            field=models.CharField(
                choices=[
                    ("submitted", "For Processing"),
                    ("for_revision", "For Revision"),
                    ("reviewed", "Approved"),
                ],
                default="submitted",
                max_length=20,
            ),
        ),
    ]
