from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0032_allow_pm_esg_as_engineer"),
    ]

    operations = [
        migrations.AddField(
            model_name="sqrsubmission",
            name="linked_request",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sqr_links",
                to="hub.request",
                verbose_name="RQ ID",
            ),
        ),
    ]
