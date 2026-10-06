from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0008_add_participant_count"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="individualregistration",
            name="division",
        ),
    ]
