from django.core.management.base import BaseCommand

from apps.registrations.models import Category

# PLACEHOLDER PRICES: nothing in the Kopala ICR 2026 site or its design
# documents the real entry fees yet. These are round placeholder numbers
# so the register -> pay -> confirm flow works locally out of the box —
# edit them in /django-admin/ (Categories) before this goes live.
CATEGORIES = [
    {
        "code": "10km-individual",
        "name": "10KM Individual Race",
        "entry_type": Category.EntryType.INDIVIDUAL,
        "price": "150.00",
        "description": "Men's Open, Women's Open, Corporate and Masters divisions.",
    },
    {
        "code": "5km-fun-run",
        "name": "5KM Fun Race & Walk",
        "entry_type": Category.EntryType.INDIVIDUAL,
        "price": "100.00",
        "description": "Untimed fun run/walk, open to all ages and fitness levels.",
    },
    {
        "code": "relay",
        "name": "10KM Corporate Relay — Team Entry",
        "entry_type": Category.EntryType.TEAM,
        "price": "800.00",
        "description": "One entry fee covers the full 8-runner team, any division.",
    },
    {
        "code": "extra-runner",
        "name": "Extra Runner Fee",
        "entry_type": Category.EntryType.TEAM,
        "price": "100.00",
        "description": "Per-runner fee for anyone added to a team's roster beyond the free 8.",
        "is_extra_fee": True,
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
                    "is_extra_fee": data.get("is_extra_fee", False),
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {category.name} ({category.code})"))
            else:
                self.stdout.write(f"Category already exists, left as-is: {category.name} ({category.code})")
