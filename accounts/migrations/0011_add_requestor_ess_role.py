from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_user_must_change_password"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("requestor", "Requestor"),
                    ("requestor_ess", "Requestor-ESS"),
                    ("engineer", "Engineer"),
                    ("admin", "Admin"),
                ],
                default="requestor",
                max_length=20,
            ),
        ),
    ]
