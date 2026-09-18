from django.core.management.base import BaseCommand

from apps.registrations.models import Category

# PLACEHOLDER PRICES: nothing in the Kopala ICR 2026 site or its design
# documents the real entry fees yet. These are round placeholder numbers
# so the register -> pay -> confirm flow works locally out of the box —
# edit them in /django-admin/ (Categories) before this goes live.
CATEGORIES = [
    {
        "code": "5km-individual",
        "name": "5KM Individual Race & Walk",
        "entry_type": Category.EntryType.INDIVIDUAL,
        "price": "2.00",
        "description": "Race it or walk it over 5KM — an easier distance for first-timers and casual runners.",
    },
    {
        "code": "10km-individual",
        "name": "10KM Individual Race",
        "entry_type": Category.EntryType.INDIVIDUAL,
        "price": "2.00",
        "description": "Men's Open, Women's Open, Corporate and Masters divisions.",
    },
    {
        "code": "21km-individual",
        "name": "21KM Individual Race & Walk",
        "entry_type": Category.EntryType.INDIVIDUAL,
        "price": "2.00",
        "description": "Race it or walk it — same divisions as the 10KM.",
    },
    {
        "code": "100m-ceo",
        "name": "100m CEO Race",
        "entry_type": Category.EntryType.INDIVIDUAL,
        "price": "2.00",
        "description": "A fun sprint reserved for company chief executives.",
    },
    {
        "code": "100m-directors",
        "name": "100m Directors Race",
        "entry_type": Category.EntryType.INDIVIDUAL,
        "price": "2.00",
        "description": "A fun sprint for company directors and senior leadership.",
    },
    {
        "code": "kids-athletics",
        "name": "Kids Athletics",
        "entry_type": Category.EntryType.INDIVIDUAL,
        "price": "2.00",
        "description": "Fun athletics activities for children on race day.",
    },
    {
        "code": "relay",
        "name": "10KM Corporate Relay — Team Entry",
        "entry_type": Category.EntryType.TEAM,
        "price": "2.00",
        "description": "One entry fee covers the full 8-runner team, any division.",
    },
    {
        "code": "exhibition-stall",
        "name": "Exhibition Stall",
        "entry_type": Category.EntryType.VENDOR,
        "price": "2.00",
        "description": "General exhibition space at the event.",
    },
    {
        "code": "food-beverage-stall",
        "name": "Food & Beverage Stall",
        "entry_type": Category.EntryType.VENDOR,
        "price": "2.00",
        "description": "For vendors selling food or drinks on race day.",
    },
    {
        "code": "corporate-activation",
        "name": "Corporate Activation",
        "entry_type": Category.EntryType.VENDOR,
        "price": "2.00",
        "description": "Branded activation space for a company to engage attendees.",
    },
    {
        "code": "official-sponsor",
        "name": "Official Sponsor",
        "entry_type": Category.EntryType.VENDOR,
        "price": "0.00",
        "description": "Complimentary category for confirmed sponsors — no payment step, confirmed immediately.",
    },
]


class Command(BaseCommand):
    help = (
        "Seed the Kopala ICR 2026 categories (PLACEHOLDER prices — edit "
        "in /django-admin/ before going live). Create-only: runs on every "
        "container boot (see docker-entrypoint.sh) but never touches a "
        "category that already exists, so price/is_active edits made in "
        "/django-admin/ are never overwritten."
    )

    def handle(self, *args, **options):
        for data in CATEGORIES:
            category, created = Category.objects.get_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "entry_type": data["entry_type"],
                    "price": data["price"],
                    "description": data["description"],
                    "currency": "ZMW",
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {category.name} ({category.code})"))
            else:
                self.stdout.write(f"Category already exists, left as-is: {category.name} ({category.code})")
