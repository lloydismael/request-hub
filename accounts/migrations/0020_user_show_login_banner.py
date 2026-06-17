from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0019_user_idle_timeout_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="show_login_banner",
            field=models.BooleanField(default=True, verbose_name="Welcome Banner on Login"),
        ),
    ]
