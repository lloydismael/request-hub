from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0033_sqrsubmission_linked_request"),
    ]

    operations = [
        migrations.AlterField(
            model_name="request",
            name="engagement_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("opportunity", "Opportunity"),
                    ("training", "Training"),
                    ("support", "Support"),
                    ("inquiry", "Inquiry"),
                    ("deployment", "Deployment"),
                    ("project_management", "Project Management"),
                    ("certification", "Certification"),
                ],
            ),
        ),
    ]
