from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0015_request_teams_chat_topic_state"),
    ]

    operations = [
        migrations.AlterField(
            model_name="request",
            name="requestor",
            field=models.ForeignKey(
                limit_choices_to={"role__in": ["requestor", "requestor_ess"]},
                on_delete=django.db.models.deletion.PROTECT,
                related_name="requests_made",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
