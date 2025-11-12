from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("hub", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StatusLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="status_logs", to=settings.AUTH_USER_MODEL)),
                ("request", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="status_logs", to="hub.request")),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
