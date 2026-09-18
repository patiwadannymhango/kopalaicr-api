from django.db import models

from apps.common.models import BaseRegistration, UUIDModel


class Category(UUIDModel):
    """
    A priced entry — an individual race distance, or the team relay's
    per-team fee. One table covers both entry types (rather than a
    separate table per type, as apps.registrations has more of these than
    the single-entry-type Kabwe reference did) — `entry_type` tells the
    public categories endpoints which rows to return.
    """

    class EntryType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        TEAM = "TEAM", "Team"
        VENDOR = "VENDOR", "Vendor"

    name = models.CharField(max_length=150)
    code = models.SlugField(max_length=100, unique=True)
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="ZMW")
    capacity = models.PositiveIntegerField(null=True, blank=True)
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
    # Only meaningful for the 5KM, 10KM and 21KM Individual races — the
    # 100m CEO/Directors races and Kids Athletics have none (matches
    # INDIVIDUAL_DIVISIONS in the frontend's src/types.ts and
    # DIVISION_RACE_CATEGORY_CODES in serializers.py).
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
        with TeamRegistration.contact so payment gateway code can treat
        both uniformly."""
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
    A company/institution's relay entry — captain details, category, and
    the roster submitted at registration time. There is no captain
    login/dashboard (removed — see git history if that's ever wanted
    back); roster changes after registration go through Django admin.
    Unlike IndividualRegistration/Participant, the registrant's contact
    details (captain_*) live directly on this model since a team has
    exactly one accountable contact.
    """

    class RelayCategory(models.TextChoices):
        MENS_TEAM = "mens-team", "Men's Team"
        WOMENS_TEAM = "womens-team", "Women's Team"
        MIXED_TEAM = "mixed-team", "Mixed Team"

    REFERENCE_PREFIX = "KICRT"

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="team_registrations",
        limit_choices_to={"entry_type": Category.EntryType.TEAM},
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
    captain_email = models.EmailField(db_index=True)
    captain_phone = models.CharField(max_length=30)

    free_runner_limit = models.PositiveIntegerField()
    accepted_terms = models.BooleanField(default=False)

    class Meta:
        ordering = ["-registered_at"]

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
    One runner on a team's roster, submitted at registration time (up to
    team.free_runner_limit — enforced in the serializer). Plain roster
    entry, not a payment target — there's no self-service way to add more
    after registration (that required the now-removed captain login); an
    admin edits the roster inline on the TeamRegistration in
    /django-admin/ if it ever needs to change.
    """

    team_registration = models.ForeignKey(TeamRegistration, on_delete=models.CASCADE, related_name="roster")
    full_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, choices=Participant.Gender.choices, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.full_name


class VendorRegistration(BaseRegistration):
    """
    A business's stall/exhibition/activation entry for the event —
    entirely separate from runners: one business, one contact, no
    roster. Like TeamRegistration, the registrant's contact details live
    directly on this model rather than through a shared Participant, since
    there's exactly one accountable contact per business.
    """

    class Requirement(models.TextChoices):
        EXHIBITION_SPACE = "exhibition-space", "Exhibition Space"
        VENDOR_STALL = "vendor-stall", "Vendor Stall"
        FOOD_BEVERAGE_STALL = "food-beverage-stall", "Food & Beverage Stall"
        CORPORATE_ACTIVATION = "corporate-activation", "Corporate Activation"
        BRANDING_PROMOTIONAL = "branding-promotional", "Branding / Promotional Space"
        OTHER = "other", "Other"

    REFERENCE_PREFIX = "KICRV"

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="vendor_registrations",
        limit_choices_to={"entry_type": Category.EntryType.VENDOR},
    )
    business_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200)
    contact_email = models.EmailField(db_index=True)
    contact_phone = models.CharField(max_length=30)
    business_location = models.CharField(max_length=200, blank=True)
    products_services = models.TextField(blank=True)
    requirement = models.CharField(max_length=30, choices=Requirement.choices, blank=True)
    accepted_terms = models.BooleanField(default=False)

    class Meta:
        ordering = ["-registered_at"]

    # --- Gateway-facing contact interface (mirrors Participant/TeamRegistration) ---

    @property
    def full_name(self):
        return self.contact_person

    @property
    def email(self):
        return self.contact_email

    @property
    def phone(self):
        return self.contact_phone

    @property
    def contact(self):
        return self

    def notify_received(self):
        from apps.notifications.services import notify_vendor_registration_received

        notify_vendor_registration_received(self)

    def notify_confirmed(self):
        from apps.notifications.services import notify_vendor_payment_confirmed

        notify_vendor_payment_confirmed(self)

    def notify_failed(self, *, reason=""):
        from apps.notifications.services import notify_vendor_payment_failed

        notify_vendor_payment_failed(self, reason=reason)
