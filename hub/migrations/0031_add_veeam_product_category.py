from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0030_sqrsubmission_revenue_unlocked"),
    ]

    operations = [
        migrations.AlterField(
            model_name="request",
            name="product_category",
            field=models.CharField(
                choices=[
                    ("Azure", "Azure"),
                    ("M365", "M365"),
                    ("VMware", "VMware"),
                    ("Omnissa", "Omnissa"),
                    ("Hybrid", "Hybrid"),
                    ("Dell", "Dell"),
                    ("HP", "HP"),
                    ("Network", "Network"),
                    ("Veeam", "Veeam"),
                    ("Others", "Others"),
                ],
                max_length=50,
            ),
        ),
    ]
