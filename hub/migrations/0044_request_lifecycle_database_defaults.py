from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0043_request_lifecycle"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE hub_request "
                "ALTER COLUMN assignment_revision SET DEFAULT 0, "
                "ALTER COLUMN lifecycle_stage SET DEFAULT 'created';"
            ),
            reverse_sql=(
                "ALTER TABLE hub_request "
                "ALTER COLUMN assignment_revision DROP DEFAULT, "
                "ALTER COLUMN lifecycle_stage DROP DEFAULT;"
            ),
        ),
    ]