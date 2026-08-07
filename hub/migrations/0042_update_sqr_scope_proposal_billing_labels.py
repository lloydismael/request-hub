from django.db import migrations, models


SCOPE_MAP = {
    "Implementation": "Deployment Only",
    "Support": "On-Call Services",
    "Managed Support and Maintenance Service": "Maintenance",
    "Managed Support and Service": "Maintenance",
    "Implementation and Project Management": "Deployment and Project Management",
    "Training": "Deployment Only",
    "Demonstration": "Deployment Only",
    "Other": "On-Call Services",
}


def forwards_map_values(apps, schema_editor):
    SqrSubmission = apps.get_model("hub", "SqrSubmission")
    for old_value, new_value in SCOPE_MAP.items():
        SqrSubmission.objects.filter(project_details=old_value).update(project_details=new_value)
    # Keep proposal_status values; only labels changed. No data rewrite needed except blank canceled.
    SqrSubmission.objects.filter(revenue_source="").update(revenue_source="")


def backwards_map_values(apps, schema_editor):
    SqrSubmission = apps.get_model("hub", "SqrSubmission")
    reverse_map = {
        "Deployment Only": "Implementation",
        "On-Call Services": "Support",
        "Maintenance": "Managed Support and Maintenance Service",
        "Deployment and Project Management": "Implementation and Project Management",
    }
    for old_value, new_value in reverse_map.items():
        SqrSubmission.objects.filter(project_details=old_value).update(project_details=new_value)
    SqrSubmission.objects.filter(proposal_status="closed_canceled").update(proposal_status="closed_lost")
    SqrSubmission.objects.filter(revenue_source="unbilled").update(revenue_source="")


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0041_alter_sqrsubmission_billing_status_choices"),
    ]

    operations = [
        migrations.RunPython(forwards_map_values, backwards_map_values),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="proposal_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("submitted_pending", "Submitted"),
                    ("negotiation_review", "On Review"),
                    ("closed_won", "Closed-Won"),
                    ("closed_lost", "Closed-Lost"),
                    ("closed_canceled", "Closed-Canceled"),
                ],
                default="",
                max_length=25,
            ),
        ),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="warranty_end_date",
            field=models.DateField(blank=True, null=True, verbose_name="Completion Warranty End Date"),
        ),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="managed_support_start_date",
            field=models.DateField(blank=True, null=True, verbose_name="Maintenance Start Date"),
        ),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="managed_support_end_date",
            field=models.DateField(blank=True, null=True, verbose_name="Maintenance End Date"),
        ),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="revenue_date",
            field=models.DateField(blank=True, null=True, verbose_name="Billed Date"),
        ),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="revenue_source",
            field=models.CharField(
                blank=True,
                choices=[
                    ("internal", "Internal"),
                    ("invoiced", "Invoiced"),
                    ("unbilled", "Unbilled"),
                ],
                max_length=100,
                verbose_name="Billing Type",
            ),
        ),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="revenue_remarks",
            field=models.TextField(blank=True, verbose_name="PO Remarks"),
        ),
        migrations.AlterField(
            model_name="sqrsubmission",
            name="revenue_overview",
            field=models.TextField(blank=True, verbose_name="Billing Remarks"),
        ),
    ]
