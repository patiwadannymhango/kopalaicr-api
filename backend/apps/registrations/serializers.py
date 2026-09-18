from rest_framework import serializers

from apps.payments.models import PaymentMethod

from .models import Category, IndividualRegistration, Participant, RosterRunner, TeamRegistration, VendorRegistration

# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------


class CategorySerializer(serializers.ModelSerializer):
    """Mirrors the frontend's BackendCategory shape exactly."""

    class Meta:
        model = Category
        fields = ("id", "name", "code", "price", "currency")


# ---------------------------------------------------------------------------
# Individual registration
# ---------------------------------------------------------------------------


class IndividualDetailsSerializer(serializers.Serializer):
    """Mirrors the frontend's IndividualDetails shape exactly (camelCase),
    so no translation layer sits between this API and the registration
    form. Used both to accept POST /registrations/individual/ and to
    render a looked-up registration back out."""

    fullName = serializers.CharField(source="participant.full_name")
    email = serializers.EmailField(source="participant.email")
    phone = serializers.CharField(source="participant.phone")
    gender = serializers.CharField(source="participant.gender")
    ageRange = serializers.CharField(source="participant.age_range")
    country = serializers.CharField(source="participant.country")
    tShirtSize = serializers.CharField(source="t_shirt_size")
    raceCategory = serializers.CharField(source="category.code")
    division = serializers.CharField()
    townOrCity = serializers.CharField(source="town_or_city")
    clubOrInstitution = serializers.CharField(source="club_or_institution")
    emergencyContactName = serializers.CharField(source="emergency_contact_name")
    emergencyContactPhone = serializers.CharField(source="emergency_contact_phone")
    medicalNotes = serializers.CharField(source="medical_notes")
    acceptedTerms = serializers.BooleanField(source="accepted_terms")


class PublicIndividualRegistrationCreateSerializer(serializers.Serializer):
    fullName = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30)
    gender = serializers.ChoiceField(choices=Participant.Gender.choices, required=False, allow_blank=True)
    ageRange = serializers.ChoiceField(choices=Participant.AgeRange.choices, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False, allow_blank=True)
    tShirtSize = serializers.ChoiceField(choices=IndividualRegistration.TShirtSize.choices, required=False, allow_blank=True)
    raceCategory = serializers.CharField()
    division = serializers.ChoiceField(choices=IndividualRegistration.Division.choices, required=False, allow_blank=True)
    townOrCity = serializers.CharField(max_length=150, required=False, allow_blank=True)
    clubOrInstitution = serializers.CharField(max_length=200, required=False, allow_blank=True)
    emergencyContactName = serializers.CharField(max_length=200, required=False, allow_blank=True)
    emergencyContactPhone = serializers.CharField(max_length=30)
    medicalNotes = serializers.CharField(required=False, allow_blank=True)
    acceptedTerms = serializers.BooleanField()

    def validate_acceptedTerms(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions.")
        return value

    def validate_raceCategory(self, value):
        try:
            return Category.objects.get(code=value, entry_type=Category.EntryType.INDIVIDUAL, is_active=True)
        except Category.DoesNotExist:
            raise serializers.ValidationError("Invalid race category.")

    # Races with divisions (Men's Open, Women's Open, Corporate, Masters)
    # — the 100m CEO/Directors races and Kids Athletics have none. Mirrors
    # DIVISION_RACE_CATEGORIES in the frontend's IndividualRegistration.tsx.
    DIVISION_RACE_CATEGORY_CODES = {"5km-individual", "10km-individual", "21km-individual"}

    def validate(self, attrs):
        category = attrs["raceCategory"]

        if category.code in self.DIVISION_RACE_CATEGORY_CODES and not attrs.get("division"):
            raise serializers.ValidationError({"division": "Please choose a division for your race."})

        if category.capacity is not None:
            current_count = IndividualRegistration.objects.filter(
                category=category,
                status__in=[
                    IndividualRegistration.Status.PENDING_PAYMENT,
                    IndividualRegistration.Status.PAYMENT_PROCESSING,
                    IndividualRegistration.Status.CONFIRMED,
                ],
            ).count()

            if current_count >= category.capacity:
                raise serializers.ValidationError({"raceCategory": "This race category has reached capacity."})

        return attrs

    def to_registration_kwargs(self):
        data = self.validated_data
        return {
            "category": data["raceCategory"],
            "participant_data": {
                "full_name": data["fullName"],
                "email": data["email"],
                "phone": data["phone"],
                "gender": data.get("gender", ""),
                "age_range": data.get("ageRange", ""),
                "country": data.get("country", ""),
            },
            "details": {
                "t_shirt_size": data.get("tShirtSize", ""),
                "division": data.get("division", ""),
                "town_or_city": data.get("townOrCity", ""),
                "club_or_institution": data.get("clubOrInstitution", ""),
                "emergency_contact_name": data.get("emergencyContactName", ""),
                "emergency_contact_phone": data["emergencyContactPhone"],
                "medical_notes": data.get("medicalNotes", ""),
                "accepted_terms": data["acceptedTerms"],
            },
        }


# ---------------------------------------------------------------------------
# Team registration / roster
# ---------------------------------------------------------------------------


class RunnerRosterEntrySerializer(serializers.Serializer):
    """Mirrors the frontend's RunnerRosterEntry shape — the roster
    submitted at team registration time."""

    fullName = serializers.CharField(max_length=200)
    gender = serializers.ChoiceField(choices=Participant.Gender.choices, required=False, allow_blank=True)


class PublicTeamRegistrationCreateSerializer(serializers.Serializer):
    teamName = serializers.CharField(max_length=200)
    companyOrInstitution = serializers.CharField(max_length=200)
    relayCategory = serializers.ChoiceField(choices=TeamRegistration.RelayCategory.choices)
    captainFirstName = serializers.CharField(max_length=150)
    captainLastName = serializers.CharField(max_length=150)
    captainEmail = serializers.EmailField()
    captainPhone = serializers.CharField(max_length=30)
    roster = RunnerRosterEntrySerializer(many=True, required=False, default=list)
    acceptedTerms = serializers.BooleanField()

    def validate_acceptedTerms(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions.")
        return value

    def validate_roster(self, value):
        from django.conf import settings

        if len(value) > settings.TEAM_FREE_RUNNER_LIMIT:
            raise serializers.ValidationError(
                f"Add up to {settings.TEAM_FREE_RUNNER_LIMIT} runners here."
            )
        return value

    def to_registration_kwargs(self):
        data = self.validated_data
        return {
            "team_name": data["teamName"],
            "company_or_institution": data["companyOrInstitution"],
            "relay_category": data["relayCategory"],
            "captain_first_name": data["captainFirstName"],
            "captain_last_name": data["captainLastName"],
            "captain_email": data["captainEmail"],
            "captain_phone": data["captainPhone"],
            "roster": data.get("roster", []),
            "accepted_terms": data["acceptedTerms"],
        }


# ---------------------------------------------------------------------------
# Vendor / exhibitor registration
# ---------------------------------------------------------------------------


class PublicVendorRegistrationCreateSerializer(serializers.Serializer):
    """Mirrors the frontend's VendorDetails shape (camelCase)."""

    businessName = serializers.CharField(max_length=200)
    contactPerson = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=30)
    email = serializers.EmailField()
    businessLocation = serializers.CharField(max_length=200, required=False, allow_blank=True)
    productsServices = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField()
    requirement = serializers.ChoiceField(choices=VendorRegistration.Requirement.choices, required=False, allow_blank=True)
    acceptedTerms = serializers.BooleanField()

    def validate_acceptedTerms(self, value):
        if not value:
            raise serializers.ValidationError("You must accept the terms and conditions.")
        return value

    def validate_category(self, value):
        try:
            return Category.objects.get(code=value, entry_type=Category.EntryType.VENDOR, is_active=True)
        except Category.DoesNotExist:
            raise serializers.ValidationError("Invalid vendor category.")

    def to_registration_kwargs(self):
        data = self.validated_data
        return {
            "category": data["category"],
            "business_name": data["businessName"],
            "contact_person": data["contactPerson"],
            "contact_email": data["email"],
            "contact_phone": data["phone"],
            "business_location": data.get("businessLocation", ""),
            "products_services": data.get("productsServices", ""),
            "requirement": data.get("requirement", ""),
            "accepted_terms": data["acceptedTerms"],
        }


# ---------------------------------------------------------------------------
# Lookup ("track your registration")
# ---------------------------------------------------------------------------


def _map_status_for_frontend(status_value, latest_payment_method=None):
    """
    The frontend's RegistrationStatus union is a small display-oriented
    set ('confirmed' | 'pending-bank-transfer' | 'processing' | 'failed'),
    narrower than BaseRegistration's full lifecycle — map down to it here
    rather than pushing that translation onto the client.
    """

    from apps.common.models import BaseRegistration

    if status_value == BaseRegistration.Status.CONFIRMED:
        return "confirmed"

    if status_value in (
        BaseRegistration.Status.CANCELLED,
        BaseRegistration.Status.EXPIRED,
        BaseRegistration.Status.REFUNDED,
    ):
        return "failed"

    if latest_payment_method == "BANK_TRANSFER":
        return "pending-bank-transfer"

    return "processing"


def serialize_individual_record(registration):
    latest_payment = registration.payments.order_by("-created_at").first()

    return {
        "reference": registration.registration_number,
        "entryType": "individual",
        "details": IndividualDetailsSerializer(registration).data,
        "payment": _payment_info(latest_payment),
        "status": _map_status_for_frontend(
            registration.status, latest_payment.payment_method if latest_payment else None
        ),
        "submittedAt": registration.registered_at.isoformat(),
        "amount": float(registration.amount),
        "currency": registration.currency,
    }


def serialize_team_record(team):
    latest_payment = team.payments.order_by("-created_at").first()

    return {
        "reference": team.registration_number,
        "entryType": "team",
        "details": {
            "teamName": team.team_name,
            "companyOrInstitution": team.company_or_institution,
            "relayCategory": team.relay_category,
            "captainFirstName": team.captain_first_name,
            "captainLastName": team.captain_last_name,
            "captainEmail": team.captain_email,
            "captainPhone": team.captain_phone,
            "roster": [{"fullName": r.full_name, "gender": r.gender} for r in team.roster.all()],
            "acceptedTerms": team.accepted_terms,
        },
        "payment": _payment_info(latest_payment),
        "status": _map_status_for_frontend(team.status, latest_payment.payment_method if latest_payment else None),
        "submittedAt": team.registered_at.isoformat(),
        "amount": float(team.amount),
        "currency": team.currency,
    }


def _payment_info(payment):
    if not payment:
        return {"method": "", "provider": "", "phoneNumber": "", "city": "", "address": "", "zipCode": ""}

    billing = payment.billing_details or {}
    return {
        "method": "card" if payment.payment_method == "CARD" else "mobile-money",
        "provider": payment.payment_method if payment.payment_method != "CARD" else "",
        "phoneNumber": billing.get("phone_number", ""),
        "city": billing.get("city", ""),
        "address": billing.get("address", ""),
        "zipCode": billing.get("zip_code", ""),
    }


# ---------------------------------------------------------------------------
# Admin-facing — Individual
# ---------------------------------------------------------------------------


class AdminParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = ("id", "full_name", "email", "phone", "gender", "age_range", "country")


class AdminIndividualRegistrationSerializer(serializers.ModelSerializer):
    """List/detail shape for the admin dashboard's Individual table."""

    participant = AdminParticipantSerializer(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_code = serializers.CharField(source="category.code", read_only=True)

    class Meta:
        model = IndividualRegistration
        fields = (
            "id",
            "registration_number",
            "status",
            "amount",
            "currency",
            "participant",
            "category",
            "category_name",
            "category_code",
            "t_shirt_size",
            "division",
            "town_or_city",
            "club_or_institution",
            "emergency_contact_name",
            "emergency_contact_phone",
            "medical_notes",
            "registered_at",
            "updated_at",
        )


class AdminIndividualRegistrationUpdateSerializer(serializers.Serializer):
    """
    PATCH payload — any mix of participant fields and registration
    fields. Deliberately no `email` field: same "can't be changed after
    registration" rule as the public/kabwe admin APIs this follows.
    """

    PARTICIPANT_FIELDS = {"full_name", "phone", "gender", "age_range", "country"}

    full_name = serializers.CharField(required=False, max_length=200)
    phone = serializers.CharField(required=False, max_length=30)
    gender = serializers.ChoiceField(choices=Participant.Gender.choices, required=False, allow_blank=True)
    age_range = serializers.ChoiceField(choices=Participant.AgeRange.choices, required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True, max_length=100)

    t_shirt_size = serializers.ChoiceField(
        choices=IndividualRegistration.TShirtSize.choices, required=False, allow_blank=True
    )
    division = serializers.ChoiceField(choices=IndividualRegistration.Division.choices, required=False, allow_blank=True)
    town_or_city = serializers.CharField(required=False, allow_blank=True, max_length=150)
    club_or_institution = serializers.CharField(required=False, allow_blank=True, max_length=200)
    emergency_contact_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    emergency_contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    medical_notes = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=IndividualRegistration.Status.choices, required=False)


class AdminManualIndividualRegistrationSerializer(serializers.Serializer):
    """POST payload for the admin's "Add person" — a walk-in/phone
    registration, same fields as the public form plus `status` and, when
    that status is CONFIRMED, the `payment_method` to record cash/EFT
    actually received under (see apps.payments.services.create_admin_cash_payment)."""

    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.filter(entry_type=Category.EntryType.INDIVIDUAL)
    )
    full_name = serializers.CharField(max_length=200)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    gender = serializers.ChoiceField(choices=Participant.Gender.choices, required=False, allow_blank=True)
    age_range = serializers.ChoiceField(choices=Participant.AgeRange.choices, required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True, max_length=100)
    t_shirt_size = serializers.ChoiceField(
        choices=IndividualRegistration.TShirtSize.choices, required=False, allow_blank=True
    )
    division = serializers.ChoiceField(choices=IndividualRegistration.Division.choices, required=False, allow_blank=True)
    town_or_city = serializers.CharField(required=False, allow_blank=True, max_length=150)
    club_or_institution = serializers.CharField(required=False, allow_blank=True, max_length=200)
    emergency_contact_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    emergency_contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    medical_notes = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=IndividualRegistration.Status.choices, default=IndividualRegistration.Status.CONFIRMED
    )
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, required=False, default=PaymentMethod.CASH)

    def to_registration_kwargs(self):
        data = self.validated_data
        return {
            "category": data["category"],
            "participant_data": {
                "full_name": data["full_name"],
                "email": data.get("email", ""),
                "phone": data.get("phone", ""),
                "gender": data.get("gender", ""),
                "age_range": data.get("age_range", ""),
                "country": data.get("country", ""),
            },
            "details": {
                "t_shirt_size": data.get("t_shirt_size", ""),
                "division": data.get("division", ""),
                "town_or_city": data.get("town_or_city", ""),
                "club_or_institution": data.get("club_or_institution", ""),
                "emergency_contact_name": data.get("emergency_contact_name", ""),
                "emergency_contact_phone": data.get("emergency_contact_phone", ""),
                "medical_notes": data.get("medical_notes", ""),
                "accepted_terms": True,
            },
            "status": data["status"],
        }


# ---------------------------------------------------------------------------
# Admin-facing — Team
# ---------------------------------------------------------------------------


class AdminRosterRunnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RosterRunner
        fields = ("id", "full_name", "gender")


class AdminTeamRegistrationSerializer(serializers.ModelSerializer):
    roster = AdminRosterRunnerSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = TeamRegistration
        fields = (
            "id",
            "registration_number",
            "status",
            "amount",
            "currency",
            "team_name",
            "company_or_institution",
            "relay_category",
            "captain_first_name",
            "captain_last_name",
            "captain_email",
            "captain_phone",
            "free_runner_limit",
            "roster",
            "category",
            "category_name",
            "registered_at",
            "updated_at",
        )


class AdminTeamRegistrationUpdateSerializer(serializers.Serializer):
    """
    PATCH payload. No `captain_email` (same "can't change after
    registration" rule) and no `roster` — roster edits stay
    Django-admin-only, per the README (this project never had a
    self-service captain dashboard to begin with).
    """

    team_name = serializers.CharField(required=False, max_length=200)
    company_or_institution = serializers.CharField(required=False, max_length=200)
    relay_category = serializers.ChoiceField(choices=TeamRegistration.RelayCategory.choices, required=False)
    captain_first_name = serializers.CharField(required=False, max_length=150)
    captain_last_name = serializers.CharField(required=False, max_length=150)
    captain_phone = serializers.CharField(required=False, max_length=30)
    status = serializers.ChoiceField(choices=TeamRegistration.Status.choices, required=False)


class AdminManualTeamRegistrationSerializer(serializers.Serializer):
    """POST payload for the admin's "Add team" — same shape as the public
    team form plus `status`/`payment_method` (see
    AdminManualIndividualRegistrationSerializer's docstring)."""

    team_name = serializers.CharField(max_length=200)
    company_or_institution = serializers.CharField(max_length=200)
    relay_category = serializers.ChoiceField(choices=TeamRegistration.RelayCategory.choices)
    captain_first_name = serializers.CharField(max_length=150)
    captain_last_name = serializers.CharField(max_length=150)
    captain_email = serializers.EmailField()
    captain_phone = serializers.CharField(max_length=30)
    roster = RunnerRosterEntrySerializer(many=True, required=False, default=list)
    status = serializers.ChoiceField(choices=TeamRegistration.Status.choices, default=TeamRegistration.Status.CONFIRMED)
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, required=False, default=PaymentMethod.CASH)

    def validate_roster(self, value):
        from django.conf import settings

        if len(value) > settings.TEAM_FREE_RUNNER_LIMIT:
            raise serializers.ValidationError(f"Add up to {settings.TEAM_FREE_RUNNER_LIMIT} runners here.")
        return value

    def to_registration_kwargs(self):
        data = self.validated_data
        return {
            "team_name": data["team_name"],
            "company_or_institution": data["company_or_institution"],
            "relay_category": data["relay_category"],
            "captain_first_name": data["captain_first_name"],
            "captain_last_name": data["captain_last_name"],
            "captain_email": data["captain_email"],
            "captain_phone": data["captain_phone"],
            "roster": data.get("roster", []),
            "accepted_terms": True,
        }
