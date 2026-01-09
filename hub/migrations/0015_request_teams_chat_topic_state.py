from django.db import migrations, models


def populate_teams_chat_topic(apps, schema_editor):
    Request = apps.get_model("hub", "Request")
    for request in Request.objects.select_related("account").all():
        topic = request.teams_chat_topic or ""
        if topic:
            continue
        reference = request.reference_code or f"REQ-{request.pk:05d}"
        account_name = request.account.name if request.account_id else ""
        if account_name:
            topic = f"{reference} · {account_name}"
        else:
            topic = reference
        Request.objects.filter(pk=request.pk).update(teams_chat_topic=topic)


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0014_requestcommunication"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE hub_request ADD COLUMN IF NOT EXISTS teams_chat_topic varchar(255) NOT NULL DEFAULT '';",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="request",
                    name="teams_chat_topic",
                    field=models.CharField(blank=True, default="", max_length=255),
                ),
            ],
        ),
        migrations.RunPython(populate_teams_chat_topic, migrations.RunPython.noop),
    ]
