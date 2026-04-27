from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0017_request_allow_pm_ess"),
    ]

    operations = [
        migrations.AlterField(
            model_name="request",
            name="engagement_type",
            field=models.CharField(
                choices=[
                    ("opportunity", "Opportunity"),
                    ("training", "Training"),
                    ("support", "Support"),
                    ("inquiry", "Inquiry"),
                    ("deployment", "Deployment"),
                    ("project_management", "Project Management"),
                ],
                max_length=20,
            ),
        ),
    ]
