from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0016_alter_user_banner_gradient"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="department",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
