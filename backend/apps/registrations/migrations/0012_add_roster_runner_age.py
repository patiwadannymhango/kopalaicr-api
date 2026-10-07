from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0011_add_team_race_categories"),
    ]

    operations = [
        migrations.AddField(
            model_name="rosterrunner",
            name="age",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
