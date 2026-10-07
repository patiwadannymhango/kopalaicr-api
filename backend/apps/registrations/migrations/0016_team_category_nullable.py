# The public form no longer has a single group-wide race category — each
# roster entry picks its own, and the group's amount is the sum of each
# entry's own category price (see services.create_team_registration).
# category stays set only for the admin's manual "Add team" flow.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0015_add_roster_runner_race_category"),
    ]

    operations = [
        migrations.AlterField(
            model_name="teamregistration",
            name="category",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"entry_type__in": ["INDIVIDUAL", "TEAM"]},
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="team_registrations",
                to="registrations.category",
            ),
        ),
    ]
