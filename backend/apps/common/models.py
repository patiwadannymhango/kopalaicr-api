import uuid

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseRegistration(UUIDModel):
    """
    Shared shape + lifecycle for anything that registers for the event and
    pays for it — IndividualRegistration and TeamRegistration. They
    otherwise have nothing in common field-wise (see each model), but both
    go through the exact same pending -> processing -> confirmed/cancelled/
    expired/refunded state machine and the exact same "no reference number
    until confirmed" rule, so that part lives here once instead of twice.

    Subclasses must set REFERENCE_PREFIX (e.g. "KICR", "KICRT") — each gets
    its own independent numbering sequence, since abstract-model
    inheritance gives every subclass its own table.

    Also defines the polymorphic interface apps.payments.services calls on
    whatever `Payment.target` resolves to (confirm_payment/fail_payment/
    mark_processing) — apps.registrations.models.RosterRunner implements
    the same interface without inheriting from this class, so that code
    never has to branch on target type. See RosterRunner's docstring.
    """

    REFERENCE_PREFIX = "REF"

    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
        PAYMENT_PROCESSING = "PAYMENT_PROCESSING", "Payment Processing"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"
        REFUNDED = "REFUNDED", "Refunded"

    # Blank until CONFIRMED — see save() below. Left unassigned rather than
    # reserved at creation so an abandoned/failed registration never
    # permanently "uses up" a number in the sequence.
    registration_number = models.CharField(max_length=50, unique=True, db_index=True, null=True, blank=True, default=None)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING_PAYMENT)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZMW")

    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.registration_number or f"unconfirmed-{self.id}"

    def save(self, *args, **kwargs):
        if self.status == self.Status.CONFIRMED and not self.registration_number:
            self.registration_number = self._generate_registration_number()

            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = list(update_fields) + ["registration_number"]

        super().save(*args, **kwargs)

    @classmethod
    def _generate_registration_number(cls):
        """
        Scanning every existing number for the max (rather than trusting
        the most-recently-confirmed row) means a single malformed
        registration_number can't get "stuck" as the reference point and
        keep producing the same already-taken number on every subsequent
        attempt.
        """

        last_number = 0

        existing_numbers = cls.objects.exclude(registration_number__isnull=True).values_list(
            "registration_number", flat=True
        )

        for registration_number in existing_numbers:
            try:
                number = int(registration_number.rsplit("-", 1)[-1])
            except (ValueError, IndexError):
                continue
            last_number = max(last_number, number)

        next_number = last_number + 1

        return f"{cls.REFERENCE_PREFIX}-{next_number:05d}"

    # --- Payment target interface (see apps.payments.services) ---------

    def mark_processing(self):
        self.status = self.Status.PAYMENT_PROCESSING
        self.save(update_fields=["status", "updated_at"])

    def confirm_payment(self):
        # Deliberately does NOT call notify_confirmed() itself —
        # apps.payments.services.apply_payment_outcome calls it after the
        # enclosing transaction commits, so a slow email/SMS send never
        # holds a database transaction open (and can't roll back a
        # successful payment if it errors).
        self.status = self.Status.CONFIRMED
        self.save(update_fields=["status", "updated_at"])

    def fail_payment(self, *, reason=""):
        # Deliberately no status change — stays PENDING_PAYMENT/
        # PAYMENT_PROCESSING so the registrant can simply retry payment.
        self.notify_failed(reason=reason)

    def notify_received(self):
        raise NotImplementedError

    def notify_confirmed(self):
        raise NotImplementedError

    def notify_failed(self, *, reason=""):
        raise NotImplementedError
