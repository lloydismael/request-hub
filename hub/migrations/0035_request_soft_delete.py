from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0034_add_certification_engagement"),
    ]

    operations = [
        migrations.AddField(
            model_name="request",
            name="is_deleted",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name="request",
            name="deleted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
