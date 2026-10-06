import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0009_remove_division"),
    ]

    operations = [
        migrations.CreateModel(
            name="IndividualRegistrationBatch",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "registration_number",
                    models.CharField(
                        blank=True, db_index=True, default=None, max_length=50, null=True, unique=True
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING_PAYMENT", "Pending Payment"),
                            ("PAYMENT_PROCESSING", "Payment Processing"),
                            ("CONFIRMED", "Confirmed"),
                            ("CANCELLED", "Cancelled"),
                            ("EXPIRED", "Expired"),
                            ("REFUNDED", "Refunded"),
                        ],
                        default="PENDING_PAYMENT",
                        max_length=30,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="ZMW", max_length=3)),
                ("registered_at", models.DateTimeField(auto_now_add=True)),
                ("submitted_by_name", models.CharField(max_length=200)),
                ("submitted_by_email", models.EmailField(max_length=254)),
                ("submitted_by_phone", models.CharField(max_length=30)),
                ("accepted_terms", models.BooleanField(default=False)),
            ],
            options={
                "ordering": ["-registered_at"],
            },
        ),
        migrations.AddField(
            model_name="individualregistration",
            name="batch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="members",
                to="registrations.individualregistrationbatch",
            ),
        ),
    ]
