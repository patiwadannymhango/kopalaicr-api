from decimal import Decimal

from django.conf import settings
from django.db import transaction

from .models import (
    Category,
    IndividualRegistration,
    IndividualRegistrationBatch,
    Participant,
    RosterRunner,
    TeamRegistration,
    VendorRegistration,
)


@transaction.atomic
def create_individual_registration(
    *,
    category,
    participant_data,
    details,
    status=IndividualRegistration.Status.PENDING_PAYMENT,
    notify=True,
):
    """
    Create the Participant + IndividualRegistration pair. `details` holds
    the registration-specific fields (club, emergency contact, medical
    notes, accepted_terms) that live on the registration rather than the
    participant.

    `notify=False` is used by create_individual_registration_batch()
    below — a batch member shouldn't get its own "registration received"
    message before the batch has even been paid for; the submitter gets
    one summary notification instead (see IndividualRegistrationBatch).
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
        town_or_city=details.get("town_or_city", ""),
        club_or_institution=details.get("club_or_institution", ""),
        emergency_contact_name=details.get("emergency_contact_name", ""),
        emergency_contact_phone=details.get("emergency_contact_phone", ""),
        medical_notes=details.get("medical_notes", ""),
        accepted_terms=details.get("accepted_terms", False),
    )

    if notify:
        registration.notify_received()

    return registration


@transaction.atomic
def create_individual_registration_batch(*, submitted_by, members):
    """
    Create several IndividualRegistrations in one go, grouped under one
    IndividualRegistrationBatch that a single Payment settles. All-or-
    nothing: the caller (PublicIndividualBatchCreateSerializer) must have
    already fully validated every member — including a cumulative
    per-category capacity check across the whole batch — before this
    runs, so there's no partial-success path to unwind here.

    `members` is a list of dicts shaped like
    {"category": Category, "participant_data": {...}, "details": {...}}
    — the same participant_data/details shapes create_individual_registration
    takes directly.
    """

    total = sum((m["category"].price for m in members), Decimal("0.00"))
    currency = members[0]["category"].currency

    batch = IndividualRegistrationBatch.objects.create(
        submitted_by_name=submitted_by["full_name"],
        submitted_by_email=submitted_by["email"].lower(),
        submitted_by_phone=submitted_by["phone"],
        accepted_terms=True,
        amount=total,
        currency=currency,
    )

    for member in members:
        registration = create_individual_registration(
            category=member["category"],
            participant_data=member["participant_data"],
            details={**member["details"], "accepted_terms": True},
            notify=False,
        )
        registration.batch = batch
        registration.save(update_fields=["batch", "updated_at"])

    batch.notify_received()

    return batch


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
    category=None,
    participant_count=None,
):
    """
    Create the team's base entry registration and its roster in one call.

    `category` is the priced TEAM Category the group is entering (5KM/10KM/
    21KM Corporate Relay, 100M CEO/Directors, Kids Athletics — all K10,000).
    Defaults to the original single "relay" (10KM Corporate Relay) category
    when not given, since the admin's manual "Add team" flow has no race
    picker of its own yet.
    """

    if category is None:
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
        participant_count=participant_count,
        free_runner_limit=settings.TEAM_FREE_RUNNER_LIMIT,
        accepted_terms=accepted_terms,
        amount=category.price,
        currency=category.currency,
    )

    for entry in roster:
        RosterRunner.objects.create(
            team_registration=team,
            full_name=entry["fullName"],
            gender=entry.get("gender", ""),
            age=entry.get("age"),
            race_category=entry.get("raceCategory", ""),
        )

    team.notify_received()

    return team


@transaction.atomic
def create_vendor_registration(
    *,
    category,
    business_name,
    contact_person,
    contact_email,
    contact_phone,
    business_location,
    products_services,
    requirement,
    accepted_terms,
):
    """
    Create the vendor's registration. A free category (e.g. Official
    Sponsor, price 0) confirms immediately — there's no payment step to
    wait on, so this jumps straight to CONFIRMED and sends the
    "confirmed" notification instead of "received" (matches the frontend's
    submitVendorRegistration/status check).
    """

    registration = VendorRegistration.objects.create(
        category=category,
        business_name=business_name,
        contact_person=contact_person,
        contact_email=contact_email.lower(),
        contact_phone=contact_phone,
        business_location=business_location,
        products_services=products_services,
        requirement=requirement,
        accepted_terms=accepted_terms,
        amount=category.price,
        currency=category.currency,
    )

    if category.price <= 0:
        registration.confirm_payment()
        registration.notify_confirmed()
    else:
        registration.notify_received()

    return registration
