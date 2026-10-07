# Swap the roster's free-number age for the same Age range choices used
# everywhere else a participant's age is collected (Participant.AgeRange).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0016_team_category_nullable"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="rosterrunner",
            name="age",
        ),
        migrations.AddField(
            model_name="rosterrunner",
            name="age_range",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Under 18", "Under 18"),
                    ("18-29", "18-29"),
                    ("30-39", "30-39"),
                    ("40-49", "40-49"),
                    ("50-59", "50-59"),
                    ("60+", "60+"),
                ],
                max_length=20,
            ),
        ),
    ]
