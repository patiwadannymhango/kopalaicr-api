# Payment no longer has a roster_runner target — removing the captain
# login/dashboard feature removed the only way to create one (the
# self-service "add an extra runner and pay for it" flow). Any existing
# payments that only had roster_runner set (no individual/team
# registration) are deleted first so the new two-way constraint can be
# added cleanly.

from django.db import migrations, models


def delete_orphaned_roster_runner_payments(apps, schema_editor):
    Payment = apps.get_model("payments", "Payment")
    Payment.objects.filter(individual_registration__isnull=True, team_registration__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(delete_orphaned_roster_runner_payments, reverse_code=migrations.RunPython.noop),
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
