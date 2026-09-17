# Payment no longer has a roster_runner target — removing the captain
# login/dashboard feature removed the only way to create one (the
# self-service "add an extra runner and pay for it" flow). The orphaned
# rows that would violate the new two-way constraint were already deleted
# in 0002.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0002_delete_orphaned_roster_runner_payments"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="payment",
            name="payment_exactly_one_target",
        ),
        migrations.RemoveField(
            model_name="payment",
            name="roster_runner",
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("individual_registration__isnull", False), ("team_registration__isnull", True)),
                    models.Q(("individual_registration__isnull", True), ("team_registration__isnull", False)),
                    _connector="OR",
                ),
                name="payment_exactly_one_target",
            ),
        ),
    ]
