from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0012_engineer_activity_log"),
    ]

    operations = [
        migrations.AlterField(
            model_name="engineeractivitylog",
            name="activity_type",
            field=models.CharField(
                choices=[
                    ("learning", "Learning"),
                    ("internal_support", "Internal Support"),
                    ("on_call_support", "On-Call Support"),
                    ("pre_sales", "Pre-Sales"),
                    ("project_management", "Project Management"),
                    ("training", "Training"),
                ],
                default="internal_support",
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="engineeractivitylog",
            name="location",
            field=models.CharField(
                choices=[("wfa", "WFA"), ("office", "Office"), ("onsite", "Onsite")],
                max_length=20,
            ),
        ),
    ]
