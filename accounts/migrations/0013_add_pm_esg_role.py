from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_add_pm_ess_role"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("requestor", "Requestor"),
                    ("requestor_ess", "Requestor-ESS"),
                    ("pm_ess", "PM-ESS"),
                    ("pm_esg", "PM-ESG"),
                    ("engineer", "Engineer"),
                    ("admin", "Admin"),
                ],
                default="requestor",
                max_length=20,
            ),
        ),
    ]
