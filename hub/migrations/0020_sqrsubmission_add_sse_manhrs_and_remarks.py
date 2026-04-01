from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hub", "0019_sqrsubmission"),
    ]

    operations = [
        migrations.AddField(
            model_name="sqrsubmission",
            name="remarks",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="sqrsubmission",
            name="sse_manhrs",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=8,
                null=True,
                validators=[MinValueValidator(0)],
            ),
        ),
    ]
