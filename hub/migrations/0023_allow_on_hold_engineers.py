from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0022_sqrsubmission_add_revenue_tracker_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="request",
            name="backup_engineer",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"role__in": ["engineer", "on_hold"]},
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="backup_requests_assigned",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="request",
            name="engineer",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"role__in": ["engineer", "on_hold"]},
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="requests_assigned",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]