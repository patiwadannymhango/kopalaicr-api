import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models

from apps.common.models import BaseRegistration, UUIDModel


class Category(UUIDModel):
    """
    A priced entry — an individual race distance, or the team relay's
    per-team / per-extra-runner fee. One table covers both entry types
    (rather than a separate table per type, as apps.registrations has more
    of these than the single-entry-type Kabwe reference did) — `entry_type`
    tells the public categories endpoints which rows to return, and
    `is_extra_fee` hides bookkeeping-only rows (the extra-runner fee) from
    those public lists without needing a second endpoint just for it.
    """

    class EntryType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        TEAM = "TEAM", "Team"

    name = models.CharField(max_length=150)
    code = models.SlugField(max_length=100, unique=True)
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZMW")
    capacity = models.PositiveIntegerField(null=True, blank=True)
    # True only for the "extra-runner" row — a real fee, but not something
    # a captain picks from a list, so it's excluded from the public
    # /categories/ endpoints and looked up by code instead (see
    # PublicExtraRunnerFeeView).
    is_extra_fee = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["entry_type", "price"]

    def __str__(self):
        return self.name


class Participant(UUIDModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    class AgeRange(models.TextChoices):
        UNDER_18 = "Under 18", "Under 18"
        AGE_18_29 = "18-29", "18-29"
        AGE_30_39 = "30-39", "30-39"
        AGE_40_49 = "40-49", "40-49"
        AGE_50_59 = "50-59", "50-59"
        AGE_60_PLUS = "60+", "60+"

    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    age_range = models.CharField(max_length=20, choices=AgeRange.choices, blank=True)
    country = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.full_name


class IndividualRegistration(BaseRegistration):
    class TShirtSize(models.TextChoices):
        XS = "XS", "XS"
        S = "S", "S"
        M = "M", "M"
        L = "L", "L"
        XL = "XL", "XL"
        XXL = "XXL", "XXL"
        XXXL = "3XL", "3XL"
        XXXXL = "4XL", "4XL"
        XXXXXL = "5XL", "5XL"

    class Division(models.TextChoices):
        MENS_OPEN = "mens-open", "Men's Open"
        WOMENS_OPEN = "womens-open", "Women's Open"
        CORPORATE = "corporate", "Corporate"
        MASTERS = "masters", "Masters"

    REFERENCE_PREFIX = "KICR"

    participant = models.ForeignKey(Participant, on_delete=models.PROTECT, related_name="registrations")
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="individual_registrations",
        limit_choices_to={"entry_type": Category.EntryType.INDIVIDUAL},
    )

    t_shirt_size = models.CharField(max_length=10, choices=TShirtSize.choices, blank=True)
    # Only meaningful for the 10KM Individual Race — the 5KM Fun Race &
    # Walk has no divisions (matches INDIVIDUAL_DIVISIONS in the
    # frontend's src/types.ts, only shown/required there when
    # raceCategory === '10km-individual').
    division = models.CharField(max_length=20, choices=Division.choices, blank=True)
    town_or_city = models.CharField(max_length=150, blank=True)
    club_or_institution = models.CharField(max_length=200, blank=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=30, blank=True)
    medical_notes = models.TextField(blank=True)
    accepted_terms = models.BooleanField(default=False)

    class Meta:
        ordering = ["-registered_at"]

    @property
    def contact(self):
        """The person to reach for this registration — generic name shared
        with TeamRegistration.contact / RosterRunner.contact so payment
        gateway code can treat all three uniformly."""
        return self.participant

    def notify_received(self):
        from apps.notifications.services import notify_individual_registration_received

        notify_individual_registration_received(self)

    def notify_confirmed(self):
        from apps.notifications.services import notify_individual_payment_confirmed

        notify_individual_payment_confirmed(self)

    def notify_failed(self, *, reason=""):
        from apps.notifications.services import notify_individual_payment_failed

        notify_individual_payment_failed(self, reason=reason)


class TeamRegistration(BaseRegistration):
    """
    A company/institution's relay entry. Doubles as the captain's login
    account — TeamAccount in the frontend's types.ts is exactly this
    record plus its roster, there's no separate "account" model. Unlike
    IndividualRegistration/Participant, the registrant's contact details
    (captain_*) live directly on this model since a team has exactly one
    accountable contact.
    """

    class RelayCategory(models.TextChoices):
        MENS_TEAM = "mens-team", "Men's Team"
        WOMENS_TEAM = "womens-team", "Women's Team"
        MIXED_TEAM = "mixed-team", "Mixed Team"

    REFERENCE_PREFIX = "KICRT"

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="team_registrations",
        limit_choices_to={"entry_type": Category.EntryType.TEAM, "is_extra_fee": False},
    )
    team_name = models.CharField(max_length=200)
    company_or_institution = models.CharField(max_length=200)
    # Which division the team competes in — display-only, not a pricing
    # key. Every relay team pays the same one `category` (code="relay")
    # regardless of this value; see the frontend's own comment in
    # TeamRegistration.tsx about looking the fee up by category code
    # rather than by this field.
    relay_category = models.CharField(max_length=20, choices=RelayCategory.choices)

    captain_first_name = models.CharField(max_length=150)
    captain_last_name = models.CharField(max_length=150)
    captain_email = models.EmailField(unique=True, db_index=True)
    captain_phone = models.CharField(max_length=30)

    password = models.CharField(max_length=128)
    # Opaque bearer token, not a JWT — see apps.registrations.auth. No
    # expiry/refresh: matches the frontend's single-stored-token model
    # (src/api/http.ts), which never refreshes or rotates it either.
    auth_token = models.CharField(max_length=64, unique=True, db_index=True)

    free_runner_limit = models.PositiveIntegerField()
    accepted_terms = models.BooleanField(default=False)

    class Meta:
        ordering = ["-registered_at"]

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    @staticmethod
    def generate_auth_token():
        return secrets.token_urlsafe(32)

    # --- Gateway-facing contact interface (mirrors Participant) --------

    @property
    def full_name(self):
        return f"{self.captain_first_name} {self.captain_last_name}".strip()

    @property
    def email(self):
        return self.captain_email

    @property
    def phone(self):
        return self.captain_phone

    @property
    def contact(self):
        return self

    def notify_received(self):
        from apps.notifications.services import notify_team_registration_received

        notify_team_registration_received(self)

    def notify_confirmed(self):
        from apps.notifications.services import notify_team_payment_confirmed

        notify_team_payment_confirmed(self)

    def notify_failed(self, *, reason=""):
        from apps.notifications.services import notify_team_payment_failed

        notify_team_payment_failed(self, reason=reason)


class RosterRunner(UUIDModel):
    """
    One runner on a team's roster. The first `team.free_runner_limit`
    runners are `covered` by the team's base entry fee; anyone added
    beyond that owes their own extra-runner fee and starts out
    `paid=False`.

    Deliberately NOT a BaseRegistration — an extra runner's payment is a
    small add-on, not a registration with its own lifecycle/reference
    number. It duck-types just enough of the interface
    apps.payments.services needs (contact/status/registration_number/
    mark_processing/confirm_payment/fail_payment) to be usable as a
    Payment target through the exact same generic payment code as
    IndividualRegistration/TeamRegistration, with no branching there. See
    apps.common.models.BaseRegistration's docstring.
    """

    team_registration = models.ForeignKey(TeamRegistration, on_delete=models.CASCADE, related_name="roster")
    full_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, choices=Participant.Gender.choices, blank=True)

    covered = models.BooleanField(default=False)
    # Always True when covered. For an extra runner, False until their fee
    # payment succeeds (see confirm_payment below).
    paid = models.BooleanField(default=False)

    # Only set for a non-covered runner — the extra-runner fee price at
    # the moment they were added, snapshotted the same way
    # BaseRegistration.amount locks in category.price at creation.
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="ZMW")

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.full_name

    @property
    def contact(self):
        # Billing details still belong to the captain — an extra runner
        # has no email/phone of their own on the roster form.
        return self.team_registration.contact

    @property
    def status(self):
        return "CONFIRMED" if self.paid else "PENDING_PAYMENT"

    @property
    def registration_number(self):
        # A roster add-on never gets its own reference. PublicPaymentStatusView
        # exposes this as `reference`, which the frontend's roster-add flow
        # ignores anyway (see TeamDashboard.tsx's usePendingPayment usage).
        return None

    def mark_processing(self):
        pass  # nothing extra to persist — Payment.status already tracks this.

    def confirm_payment(self):
        self.paid = True
        self.save(update_fields=["paid", "updated_at"])

    def fail_payment(self, *, reason=""):
        pass  # stays paid=False; the captain just retries from the dashboard.
