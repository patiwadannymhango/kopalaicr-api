# The event lineup grew from 3 race formats to 7 (see the frontend's
# src/data/event.ts RACE_FORMATS): 5KM Individual Race & Walk (renamed
# in place from the old, never-registered-for "5km-fun-run"), 21KM
# Individual Race & Walk, 100m CEO Race, 100m Directors Race, and Kids
# Athletics. Real entry fees haven't been decided yet, so every
# category — including the two that already had seeded prices — is set
# to the same K2 placeholder used on the frontend until the organisers
# confirm real pricing in /django-admin/.

from decimal import Decimal

from django.db import migrations

PLACEHOLDER_PRICE = Decimal("2.00")

NEW_INDIVIDUAL_CATEGORIES = [
    {
        "code": "21km-individual",
        "name": "21KM Individual Race & Walk",
        "description": "Race it or walk it — same divisions as the 10KM.",
    },
    {
        "code": "100m-ceo",
        "name": "100m CEO Race",
        "description": "A fun sprint reserved for company chief executives.",
    },
    {
        "code": "100m-directors",
        "name": "100m Directors Race",
        "description": "A fun sprint for company directors and senior leadership.",
    },
    {
        "code": "kids-athletics",
        "name": "Kids Athletics",
        "description": "Fun athletics activities for children on race day.",
    },
]


def update_race_categories(apps, schema_editor):
    Category = apps.get_model("registrations", "Category")

    # Rename in place — matches the frontend's renamed '5km-individual'
    # code exactly, and nobody has registered under the old code yet.
    Category.objects.filter(code="5km-fun-run").update(
        code="5km-individual",
        name="5KM Individual Race & Walk",
        description="Race it or walk it over 5KM — an easier distance for first-timers and casual runners.",
    )

    Category.objects.all().update(price=PLACEHOLDER_PRICE)

    for data in NEW_INDIVIDUAL_CATEGORIES:
        Category.objects.get_or_create(
            code=data["code"],
            defaults={
                "name": data["name"],
                "entry_type": "INDIVIDUAL",
                "price": PLACEHOLDER_PRICE,
                "description": data["description"],
                "currency": "ZMW",
                "is_active": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0003_remove_team_login"),
    ]

    operations = [
        migrations.RunPython(update_race_categories, reverse_code=migrations.RunPython.noop),
    ]
