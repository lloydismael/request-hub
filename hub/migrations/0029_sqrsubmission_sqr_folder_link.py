from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0028_discount_rate_no_discount"),
    ]

    operations = [
        migrations.AddField(
            model_name="sqrsubmission",
            name="sqr_folder_link",
            field=models.URLField(blank=True),
        ),
    ]
