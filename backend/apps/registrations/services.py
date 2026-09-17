from django.conf import settings
from django.db import transaction

from .models import Category, IndividualRegistration, Participant, RosterRunner, TeamRegistration


@transaction.atomic
def create_individual_registration(
    *,
    category,
    participant_data,
    details,
    status=IndividualRegistration.Status.PENDING_PAYMENT,
):
    """
    Create the Participant + IndividualRegistration pair. `details` holds
    the registration-specific fields (t-shirt size, division, club,
    emergency contact, medical notes, accepted_terms) that live on the
    registration rather than the participant.
    """

    participant = Participant.objects.create(
        full_name=participant_data["full_name"],
        email=participant_data.get("email", ""),
        phone=participant_data.get("phone", ""),
        gender=participant_data.get("gender", ""),
        age_range=participant_data.get("age_range", ""),
        country=participant_data.get("country", ""),
    )

    registration = IndividualRegistration.objects.create(
        participant=participant,
        category=category,
        status=status,
        amount=category.price,
        currency=category.currency,
        t_shirt_size=details.get("t_shirt_size", ""),
        division=details.get("division", ""),
        town_or_city=details.get("town_or_city", ""),
        club_or_institution=details.get("club_or_institution", ""),
        emergency_contact_name=details.get("emergency_contact_name", ""),
        emergency_contact_phone=details.get("emergency_contact_phone", ""),
        medical_notes=details.get("medical_notes", ""),
        accepted_terms=details.get("accepted_terms", False),
    )

    registration.notify_received()

    return registration


@transaction.atomic
def create_team_registration(
    *,
    team_name,
    company_or_institution,
    relay_category,
    captain_first_name,
    captain_last_name,
    captain_email,
    captain_phone,
    roster,
    accepted_terms,
):
    """
    Create the team's base entry registration and its roster in one call.
    """

    category = Category.objects.get(code="relay", entry_type=Category.EntryType.TEAM, is_active=True)

    team = TeamRegistration.objects.create(
        category=category,
        team_name=team_name,
        company_or_institution=company_or_institution,
        relay_category=relay_category,
        captain_first_name=captain_first_name,
        captain_last_name=captain_last_name,
        captain_email=captain_email.lower(),
        captain_phone=captain_phone,
        free_runner_limit=settings.TEAM_FREE_RUNNER_LIMIT,
        accepted_terms=accepted_terms,
        amount=category.price,
        currency=category.currency,
    )

    for entry in roster[: settings.TEAM_FREE_RUNNER_LIMIT]:
        RosterRunner.objects.create(
            team_registration=team,
            full_name=entry["fullName"],
            gender=entry.get("gender", ""),
        )

    team.notify_received()

    return team
