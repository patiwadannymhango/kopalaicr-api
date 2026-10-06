import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0005_add_vendor_registration"),
        ("registrations", "0010_add_individual_registration_batch"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="payment",
            name="payment_exactly_one_target",
        ),
        migrations.AddField(
            model_name="payment",
            name="individual_registration_batch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="payments",
                to="registrations.individualregistrationbatch",
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("individual_registration__isnull", False),
                        ("individual_registration_batch__isnull", True),
                        ("team_registration__isnull", True),
                        ("vendor_registration__isnull", True),
                    ),
                    models.Q(
                        ("individual_registration__isnull", True),
                        ("individual_registration_batch__isnull", False),
                        ("team_registration__isnull", True),
                        ("vendor_registration__isnull", True),
                    ),
                    models.Q(
                        ("individual_registration__isnull", True),
                        ("individual_registration_batch__isnull", True),
                        ("team_registration__isnull", False),
                        ("vendor_registration__isnull", True),
                    ),
                    models.Q(
                        ("individual_registration__isnull", True),
                        ("individual_registration_batch__isnull", True),
                        ("team_registration__isnull", True),
                        ("vendor_registration__isnull", False),
                    ),
                    _connector="OR",
                ),
                name="payment_exactly_one_target",
            ),
        ),
    ]
