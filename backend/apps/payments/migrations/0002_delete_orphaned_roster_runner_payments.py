# Split from the schema changes in 0003 for the same reason as
# registrations/migrations/0002_delete_extra_runner_category.py: deleting
# rows from payments_payment and then ALTER TABLE-ing that same table in
# one transaction hits Postgres's "cannot ALTER TABLE ... because it has
# pending trigger events" (its FKs are DEFERRABLE INITIALLY DEFERRED).

from django.db import migrations


def delete_orphaned_roster_runner_payments(apps, schema_editor):
    Payment = apps.get_model("payments", "Payment")
    Payment.objects.filter(individual_registration__isnull=True, team_registration__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(delete_orphaned_roster_runner_payments, reverse_code=migrations.RunPython.noop),
    ]
