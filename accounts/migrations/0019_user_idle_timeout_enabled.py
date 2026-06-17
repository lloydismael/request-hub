from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0018_user_show_chatbot"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="idle_timeout_enabled",
            field=models.BooleanField(default=True, verbose_name="5-Minute Idle Timeout"),
        ),
    ]
