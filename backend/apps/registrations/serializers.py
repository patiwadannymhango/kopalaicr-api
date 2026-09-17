from rest_framework import serializers

from .models import Category, IndividualRegistration, Participant, TeamRegistration

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

    def validate(self, attrs):
        category = attrs["raceCategory"]

        if category.code == "10km-individual" and not attrs.get("division"):
            raise serializers.ValidationError({"division": "Please choose a division for the 10KM Individual Race."})

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
