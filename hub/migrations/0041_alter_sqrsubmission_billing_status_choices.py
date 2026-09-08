from django.db import migrations, models


def forwards_map_revenue_status(apps, schema_editor):
    SqrSubmission = apps.get_model("hub", "SqrSubmission")
    SqrSubmission.objects.filter(revenue_status="invoiced").update(revenue_status="billed")
    SqrSubmission.objects.filter(revenue_status="partial").update(revenue_status="billed")
    SqrSubmission.objects.filter(revenue_status="pending").update(revenue_status="not_yet_billed")
    # Legacy rows that only had a revenue date should count as billed.
    SqrSubmission.objects.filter(revenue_status="", revenue_date__isnull=False).update(revenue_status="billed")


def backwards_map_revenue_status(apps, schema_editor):
    SqrSubmission = apps.get_model("hub", "SqrSubmission")
    SqrSubmission.objects.filter(revenue_status="billed").update(revenue_status="invoiced")
    SqrSubmission.objects.filter(revenue_status="not_yet_billed").update(revenue_status="pending")


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0040_rename_sqrsubmissionhistory_indexes"),
    ]

    operations = [
        migrations.RunPython(forwards_map_revenue_status, backwards_map_revenue_status),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="revenue_date",
            field=models.DateField(blank=True, null=True, verbose_name="Date"),
        ),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="revenue_reference_no",
            field=models.CharField(blank=True, max_length=100, verbose_name="Billing Reference"),
        ),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="revenue_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("billed", "Billed"),
                    ("not_yet_billed", "Not Yet Billed"),
                ],
                default="",
                max_length=20,
                verbose_name="Billing Status",
            ),
        ),
    ]
