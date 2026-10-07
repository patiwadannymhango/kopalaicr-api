# Group registration now offers the same race list as Individual entry
# (same Category rows, same per-person price — a group pays that one
# flat amount for its whole declared headcount) plus the one genuinely
# team-only category, 10KM Corporate Relay, at its own flat K10,000
# rate. The 5 team-only "Corporate Relay"-named categories added in
# 0011 (5KM/21KM Corporate Relay, 100M CEO/Directors, KIDS Athletics)
# are retired — deactivated, not deleted, since Category rows are
# PROTECTed and this keeps any already-created registrations intact.

from django.db import migrations, models
import django.db.models.deletion

RETIRED_TEAM_CATEGORY_CODES = [
    "5km-corporate-relay",
    "21km-corporate-relay",
    "100m-ceo-relay",
    "100m-directors-relay",
    "kids-athletics-relay",
]


def retire_team_only_categories(apps, schema_editor):
    Category = apps.get_model("registrations", "Category")
    Category.objects.filter(code__in=RETIRED_TEAM_CATEGORY_CODES).update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0013_make_team_lead_optional"),
    ]

    operations = [
        migrations.RunPython(retire_team_only_categories, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name="teamregistration",
            name="category",
            field=models.ForeignKey(
                limit_choices_to={"entry_type__in": ["INDIVIDUAL", "TEAM"]},
                on_delete=django.db.models.deletion.PROTECT,
                related_name="team_registrations",
                to="registrations.category",
            ),
        ),
    ]
