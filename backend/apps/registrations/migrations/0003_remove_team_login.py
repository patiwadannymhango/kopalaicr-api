# Removes the captain login/dashboard feature: TeamRegistration no longer
# has a password or auth_token, RosterRunner is a plain roster entry
# (no more covered/paid/amount/currency — that was only for the
# now-removed self-service "add an extra runner and pay for it" flow),
# and Category loses is_extra_fee (its one real usage, the "extra-runner"
# row, was deleted in 0002).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0002_delete_extra_runner_category"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="category",
            name="is_extra_fee",
        ),
        migrations.RemoveField(
            model_name="teamregistration",
            name="password",
        ),
        migrations.RemoveField(
            model_name="teamregistration",
            name="auth_token",
        ),
        migrations.AlterField(
            model_name="teamregistration",
            name="captain_email",
            field=models.EmailField(db_index=True, max_length=254),
        ),
        migrations.AlterField(
            model_name="teamregistration",
            name="category",
            field=models.ForeignKey(
                limit_choices_to={"entry_type": "TEAM"},
                on_delete=django.db.models.deletion.PROTECT,
                related_name="team_registrations",
                to="registrations.category",
            ),
        ),
        migrations.RemoveField(
            model_name="rosterrunner",
            name="covered",
        ),
        migrations.RemoveField(
            model_name="rosterrunner",
            name="paid",
        ),
        migrations.RemoveField(
            model_name="rosterrunner",
            name="amount",
        ),
        migrations.RemoveField(
            model_name="rosterrunner",
            name="currency",
        ),
    ]
