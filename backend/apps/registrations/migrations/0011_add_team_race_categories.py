# The relay was a single K10,000 "10KM Corporate Relay" team entry.
# Group registrations now pick from the same lineup of race formats as
# individuals (5KM/10KM/21KM, 100m CEO, 100m Directors, Kids Athletics)
# as a team entry, all priced at the flat K10,000 group rate.

from decimal import Decimal

from django.db import migrations

TEAM_PRICE = Decimal("10000.00")

RENAME_RELAY = {
    "name": "10KM Corporate Relay",
    "description": "One entry fee covers the full group, any division.",
}

NEW_TEAM_CATEGORIES = [
    {
        "code": "5km-corporate-relay",
        "name": "5KM Corporate Relay",
        "description": "One entry fee covers the full group, any division.",
    },
    {
        "code": "21km-corporate-relay",
        "name": "21KM Corporate Relay",
        "description": "One entry fee covers the full group, any division.",
    },
    {
        "code": "100m-ceo-relay",
        "name": "100M CEO Race",
        "description": "Group entry for the CEO sprint.",
    },
    {
        "code": "100m-directors-relay",
        "name": "100M Directors Race",
        "description": "Group entry for the Directors sprint.",
    },
    {
        "code": "kids-athletics-relay",
        "name": "KIDS Athletics",
        "description": "Group entry for Kids Athletics.",
    },
]


def add_team_race_categories(apps, schema_editor):
    Category = apps.get_model("registrations", "Category")

    Category.objects.filter(code="relay").update(**RENAME_RELAY)

    for data in NEW_TEAM_CATEGORIES:
        Category.objects.get_or_create(
            code=data["code"],
            defaults={
                "name": data["name"],
                "entry_type": "TEAM",
                "price": TEAM_PRICE,
                "description": data["description"],
                "currency": "ZMW",
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0010_add_individual_registration_batch"),
    ]

    operations = [
        migrations.RunPython(add_team_race_categories, reverse_code=migrations.RunPython.noop),
    ]
