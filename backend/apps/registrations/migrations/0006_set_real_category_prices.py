# Real entry fees, from the official event advert/jingle script (KCM
# KOPALA Inter-Company Relay 2026): 21KM/10KM Individual and 5KM Health
# Walk at K400, 10KM Corporate Relay and Corporate Exhibition at
# K10,000, 100m CEO Race at K2,000, 100m Directors Race at K1,500, and
# Kids Athletics at K200. Replaces the K2 placeholder set in
# 0004_update_race_categories. The three paid vendor/exhibitor
# categories all share the one "Corporate Exhibition" rate the advert
# gives; official-sponsor stays free (complimentary, not priced in the
# advert).

from decimal import Decimal

from django.db import migrations

REAL_PRICES = {
    "5km-individual": Decimal("400.00"),
    "10km-individual": Decimal("400.00"),
    "21km-individual": Decimal("400.00"),
    "100m-ceo": Decimal("2000.00"),
    "100m-directors": Decimal("1500.00"),
    "kids-athletics": Decimal("200.00"),
    "relay": Decimal("10000.00"),
    "exhibition-stall": Decimal("10000.00"),
    "food-beverage-stall": Decimal("10000.00"),
    "corporate-activation": Decimal("10000.00"),
}


def set_real_prices(apps, schema_editor):
    Category = apps.get_model("registrations", "Category")
    for code, price in REAL_PRICES.items():
        Category.objects.filter(code=code).update(price=price)


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0005_add_vendor_registration"),
    ]

    operations = [
        migrations.RunPython(set_real_prices, reverse_code=migrations.RunPython.noop),
    ]
