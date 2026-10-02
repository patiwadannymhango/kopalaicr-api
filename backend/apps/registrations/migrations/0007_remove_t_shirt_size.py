from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0006_set_real_category_prices"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="individualregistration",
            name="t_shirt_size",
        ),
    ]
