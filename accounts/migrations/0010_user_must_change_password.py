from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_database_profile_photos"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="must_change_password",
            field=models.BooleanField(default=False),
        ),
    ]
