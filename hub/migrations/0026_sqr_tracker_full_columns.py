import django.db.models.deletion
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0025_sqr_proposal_and_delivery"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Proposal Stage extra fields (M, O, P, V) ───────────────────────
        migrations.AddField(
            model_name="sqrsubmission",
            name="sse_amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=14, null=True,
                validators=[MinValueValidator(0)],
                help_text="SSE labour cost (PHP).",
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="pm_amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=14, null=True,
                validators=[MinValueValidator(0)],
                help_text="PM labour cost (PHP).",
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="managed_support_amount",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=14, null=True,
                validators=[MinValueValidator(0)],
                help_text="Managed Support Service amount (PHP).",
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="validity_due_date",
            field=models.DateField(blank=True, null=True),
        ),
        # ── Service Delivery Stage extra fields (X–AK) ─────────────────────
        migrations.AddField(
            model_name="sqrsubmission",
            name="po_pnl_date",
            field=models.DateField(blank=True, null=True, verbose_name="PO/PNL Date"),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="assigned_pm",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sqr_assigned_pm",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Assigned PM",
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="assigned_sse",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sqr_assigned_sse",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Assigned SSE",
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="overall_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("on_hold", "On Hold"),
                    ("planning", "Planning"),
                    ("in_progress", "In Progress"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="key_updates_risks",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="warranty_end_date",
            field=models.DateField(blank=True, null=True, verbose_name="Post-service Warranty End Date"),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="managed_support_start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="managed_support_end_date",
            field=models.DateField(blank=True, null=True),
        ),
        # ── Revenue Stage fields (AL–AP) ────────────────────────────────────
        migrations.AddField(
            model_name="sqrsubmission",
            name="revenue_date",
            field=models.DateField(blank=True, null=True, verbose_name="SI/Revenue Date"),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="revenue_source",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="revenue_reference_no",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="revenue_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("invoiced", "Invoiced"),
                    ("partial", "Partial"),
                    ("pending", "Pending"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="revenue_remarks",
            field=models.TextField(blank=True),
        ),
    ]
