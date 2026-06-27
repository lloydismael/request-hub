from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0036_sqrsubmission_revenue_declaration"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="sqrsubmission",
            constraint=models.UniqueConstraint(
                fields=("linked_request",),
                condition=Q(("linked_request__isnull", False)),
                name="unique_sqrsubmission_linked_request",
            ),
        ),
    ]
