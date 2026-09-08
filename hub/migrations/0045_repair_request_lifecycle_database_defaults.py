from django.db import migrations


def repair_request_lifecycle_database_defaults(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    schema_editor.execute(
        "ALTER TABLE hub_request "
        "ALTER COLUMN assignment_revision SET DEFAULT 0, "
        "ALTER COLUMN lifecycle_stage SET DEFAULT 'created';"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0044_request_lifecycle_database_defaults"),
    ]

    operations = [
        migrations.RunPython(
            repair_request_lifecycle_database_defaults,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
