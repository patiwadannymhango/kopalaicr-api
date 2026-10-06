import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_add_vendor_registration"),
        ("registrations", "0010_add_individual_registration_batch"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="individual_registration_batch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="registrations.individualregistrationbatch",
            ),
        ),
    ]
