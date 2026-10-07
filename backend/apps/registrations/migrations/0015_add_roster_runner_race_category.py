from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0014_team_uses_individual_categories"),
    ]

    operations = [
        migrations.AddField(
            model_name="rosterrunner",
            name="race_category",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
