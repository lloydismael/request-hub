from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0029_sqrsubmission_sqr_folder_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="sqrsubmission",
            name="revenue_unlocked",
            field=models.BooleanField(
                default=False,
                help_text="Set to True when PM clicks 'To Revenue' in Step 3 to enable Step 4.",
            ),
        ),
    ]
