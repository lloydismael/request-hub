from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_add_on_hold_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="banner_gradient",
            field=models.CharField(
                blank=True,
                default="blue",
                max_length=20,
            ),
        ),
    ]
