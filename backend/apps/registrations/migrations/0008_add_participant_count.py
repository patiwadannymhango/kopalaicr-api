from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0007_remove_t_shirt_size"),
    ]

    operations = [
        migrations.AddField(
            model_name="teamregistration",
            name="participant_count",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
