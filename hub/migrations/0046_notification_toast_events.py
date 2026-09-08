from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0045_repair_request_lifecycle_database_defaults"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="event_key",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
        migrations.AddField(
            model_name="notification",
            name="event_revision",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="notification",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("system", "System"),
                    ("new_request", "New Request"),
                    ("assignment", "Assignment"),
                ],
                db_index=True,
                default="system",
                max_length=32,
            ),
        ),
        migrations.AddConstraint(
            model_name="notification",
            constraint=models.UniqueConstraint(
                condition=~models.Q(event_key=""),
                fields=("recipient", "event_key"),
                name="uniq_notif_recipient_event_key",
            ),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["recipient", "event_type", "id"],
                name="notif_rec_evt_id",
            ),
        ),
    ]
