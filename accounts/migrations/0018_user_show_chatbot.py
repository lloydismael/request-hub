from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0017_user_department"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="show_chatbot",
            field=models.BooleanField(default=True, verbose_name="Show AI Chatbot"),
        ),
    ]
