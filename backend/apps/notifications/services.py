"""
High-level "tell the registrant what just happened" functions — the rest
of the codebase (registration/payment services, webhooks, admin actions)
calls these; they compose the message and fire email + SMS where
appropriate.

Only one email goes out per registration lifecycle: the "confirmed" email
in notify_*_payment_confirmed(), sent once the registration/team entry
actually succeeds (payment settles, or an admin marks it CONFIRMED).
notify_*_registration_received/notify_*_payment_failed intentionally send
SMS only — no "received" email while payment is still pending, and no
failure email — so a registrant never receives more than one email out of
this flow.
"""

from django.conf import settings
from django.template.loader import render_to_string

from .email import send_email
from .models import Notification
from .sms import send_sms

# ---------------------------------------------------------------------------
# Individual registrations
# ---------------------------------------------------------------------------


def notify_individual_registration_received(registration):
    participant = registration.participant

    # No reference number yet — one is only assigned once the
    # registration is confirmed (see BaseRegistration.save()), so there's
    # nothing to quote here. The registrant can still be found by email if
    # they need to look this up before then.
    text = (
        f"Hi {participant.full_name},\n\n"
        f"We've received your registration for {settings.EVENT_NAME}.\n"
        f"Category: {registration.category.name}\n"
        f"Amount due: {registration.currency} {registration.amount}\n\n"
        "Complete payment to confirm your place and receive your registration reference.\n"
    )

    if participant.phone:
        send_sms(
            to=participant.phone,
            message=text,
            target=registration,
            notification_type=Notification.NotificationType.REGISTRATION_RECEIVED,
        )


def notify_individual_payment_confirmed(registration):
    """The one email a registrant gets: sent once the registration
    actually succeeds — a real payment settling, or an admin marking it
    CONFIRMED."""

    participant = registration.participant

    subject = f"You're confirmed — {registration.registration_number}"
    text = (
        f"Hi {participant.full_name},\n\n"
        f"Your entry for {settings.EVENT_NAME} is confirmed and paid. This "
        "email is your proof of registration — keep it handy for race "
        "pack collection.\n\n"
        f"Reference: {registration.registration_number}\n"
        f"Race category: {registration.category.name}\n"
        f"Amount paid: {registration.currency} {registration.amount}\n"
        f"Event date: {settings.EVENT_DATE}\n"
        f"Venue: {settings.EVENT_LOCATION}\n\n"
        "On race day, bring a valid ID and this reference number to "
        "collect your race pack.\n\n"
        "See you at the start line.\n"
    )

    track_url = f"{settings.PUBLIC_SITE_URL}/#track" if settings.PUBLIC_SITE_URL else "#"

    html = render_to_string(
        "notifications/emails/individual_registration_confirmed.html",
        {
            "first_name": participant.full_name.split(" ")[0] if participant.full_name else "",
            "event_name": settings.EVENT_NAME,
            "reference": registration.registration_number,
            "category_name": registration.category.name,
            "currency": registration.currency,
            "amount": registration.amount,
            "event_date": settings.EVENT_DATE,
            "event_location": settings.EVENT_LOCATION,
            "track_url": track_url,
            "contact_email": settings.EVENT_CONTACT_EMAIL or settings.DEFAULT_FROM_EMAIL,
            "contact_phone": settings.EVENT_CONTACT_PHONE,
        },
    )

    if participant.email:
        send_email(
            to=participant.email,
            subject=subject,
            text_body=text,
            html_body=html,
            target=registration,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
        )

    if participant.phone:
        send_sms(
            to=participant.phone,
            message=text,
            target=registration,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
        )


def notify_individual_payment_failed(registration, *, reason=""):
    participant = registration.participant

    # A failed payment never reached CONFIRMED, so there's no reference
    # number to quote (see BaseRegistration.save()).
    text = (
        f"Hi {participant.full_name},\n\n"
        f"We couldn't confirm your payment for {settings.EVENT_NAME}"
        f"{f' ({reason})' if reason else ''}.\n\n"
        "Please try again, or contact us for help.\n"
    )

    if participant.phone:
        send_sms(
            to=participant.phone,
            message=text,
            target=registration,
            notification_type=Notification.NotificationType.PAYMENT_FAILED,
        )


# ---------------------------------------------------------------------------
# Team (relay) registrations — same lifecycle/notification shape as
# individuals (see module docstring), addressed to the captain, worded
# around the team entry + dashboard login rather than a single runner.
# ---------------------------------------------------------------------------


def notify_team_registration_received(team):
    text = (
        f"Hi {team.captain_first_name},\n\n"
        f"We've received {team.team_name}'s registration for {settings.EVENT_NAME}.\n"
        f"Category: 10KM Corporate Relay\n"
        f"Amount due: {team.currency} {team.amount}\n\n"
        "Complete payment to confirm your team's place and receive your registration reference. "
        "Your team login is already set up — sign in anytime to manage your roster.\n"
    )

    if team.captain_phone:
        send_sms(
            to=team.captain_phone,
            message=text,
            target=team,
            notification_type=Notification.NotificationType.REGISTRATION_RECEIVED,
        )


def notify_team_payment_confirmed(team):
    """The one email a captain gets — mirrors notify_individual_payment_confirmed."""

    subject = f"You're confirmed — {team.registration_number}"
    text = (
        f"Hi {team.captain_first_name},\n\n"
        f"{team.team_name}'s entry for {settings.EVENT_NAME} is confirmed and paid. This "
        "email is your proof of registration — keep it handy for race pack collection.\n\n"
        f"Reference: {team.registration_number}\n"
        f"Team: {team.team_name} ({team.company_or_institution})\n"
        f"Amount paid: {team.currency} {team.amount}\n"
        f"Event date: {settings.EVENT_DATE}\n"
        f"Venue: {settings.EVENT_LOCATION}\n\n"
        f"Sign in at {settings.PUBLIC_SITE_URL or 'the site'} with {team.captain_email} to manage your roster — "
        f"the first {team.free_runner_limit} runners are covered by this entry fee; anyone added beyond that "
        "incurs a small extra-runner fee.\n\n"
        "See you at the start line.\n"
    )

    html = render_to_string(
        "notifications/emails/team_registration_confirmed.html",
        {
            "captain_first_name": team.captain_first_name,
            "event_name": settings.EVENT_NAME,
            "reference": team.registration_number,
            "team_name": team.team_name,
            "company_or_institution": team.company_or_institution,
            "currency": team.currency,
            "amount": team.amount,
            "event_date": settings.EVENT_DATE,
            "event_location": settings.EVENT_LOCATION,
            "free_runner_limit": team.free_runner_limit,
            "site_url": settings.PUBLIC_SITE_URL or "",
            "contact_email": settings.EVENT_CONTACT_EMAIL or settings.DEFAULT_FROM_EMAIL,
            "contact_phone": settings.EVENT_CONTACT_PHONE,
        },
    )

    if team.captain_email:
        send_email(
            to=team.captain_email,
            subject=subject,
            text_body=text,
            html_body=html,
            target=team,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
        )

    if team.captain_phone:
        send_sms(
            to=team.captain_phone,
            message=text,
            target=team,
            notification_type=Notification.NotificationType.PAYMENT_CONFIRMED,
        )


def notify_team_payment_failed(team, *, reason=""):
    text = (
        f"Hi {team.captain_first_name},\n\n"
        f"We couldn't confirm payment for {team.team_name}'s registration for "
        f"{settings.EVENT_NAME}{f' ({reason})' if reason else ''}.\n\n"
        "Please try again, or contact us for help.\n"
    )

    if team.captain_phone:
        send_sms(
            to=team.captain_phone,
            message=text,
            target=team,
            notification_type=Notification.NotificationType.PAYMENT_FAILED,
        )
