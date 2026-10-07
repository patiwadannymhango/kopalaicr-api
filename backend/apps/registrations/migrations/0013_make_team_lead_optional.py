# "Captain" (internal name, unchanged) is "Team Lead" on the public
# form, and no longer required — these were NOT NULL CharField/EmailField
# columns already happy to store '', so this only changes `blank`
# (validation leniency), not the DB schema itself.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0012_add_roster_runner_age"),
    ]

    operations = [
        migrations.AlterField(
            model_name="teamregistration",
            name="captain_first_name",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AlterField(
            model_name="teamregistration",
            name="captain_last_name",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AlterField(
            model_name="teamregistration",
            name="captain_email",
            field=models.EmailField(blank=True, db_index=True, max_length=254),
        ),
        migrations.AlterField(
            model_name="teamregistration",
            name="captain_phone",
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
