# Split out from the schema changes in 0003 on purpose: Postgres refuses
# to ALTER TABLE a table in the same transaction as a DML statement
# (DELETE here) against it when there are DEFERRABLE INITIALLY DEFERRED
# FK triggers involved ("cannot ALTER TABLE ... because it has pending
# trigger events") — registrations_category has exactly that, referenced
# by individualregistration/teamregistration. Two migrations = two
# transactions = no conflict.

from django.db import migrations


def delete_extra_runner_category(apps, schema_editor):
    Category = apps.get_model("registrations", "Category")
    Category.objects.filter(code="extra-runner").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(delete_extra_runner_category, reverse_code=migrations.RunPython.noop),
    ]
