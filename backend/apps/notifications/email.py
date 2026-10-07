"""
Email sending, using Django's built-in SMTP backend configured in
settings (EMAIL_HOST_USER / EMAIL_HOST_PASSWORD — a Gmail App Password
works well). In development EMAIL_BACKEND defaults to the console
backend, so emails just print instead of needing real credentials.

Every send is logged to the Notification model regardless of success or
failure, so delivery status per registration is visible in the admin.
"""

from email.mime.image import MIMEImage
from pathlib import Path

from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from .models import Notification

# Referenced by every HTML email template as <img src="cid:event-logo">.
# Attached inline (not linked by URL) so the logo renders even though
# nothing in this project serves images at a stable public URL yet.
LOGO_PATH = Path(__file__).resolve().parent / "templates" / "notifications" / "emails" / "assets" / "logo.png"


def send_email(*, to, subject, text_body, html_body=None, target=None, notification_type=Notification.NotificationType.CUSTOM):
    from apps.registrations.models import (
        IndividualRegistration,
        IndividualRegistrationBatch,
        TeamRegistration,
        VendorRegistration,
    )

    notification = Notification.objects.create(
        individual_registration=target if isinstance(target, IndividualRegistration) else None,
        individual_registration_batch=target if isinstance(target, IndividualRegistrationBatch) else None,
        team_registration=target if isinstance(target, TeamRegistration) else None,
        vendor_registration=target if isinstance(target, VendorRegistration) else None,
        channel=Notification.Channel.EMAIL,
        notification_type=notification_type,
        recipient=to,
        subject=subject,
        body=text_body,
        status=Notification.Status.PENDING,
    )

    try:
        message = EmailMultiAlternatives(subject=subject, body=text_body, to=[to])

        if html_body:
            message.attach_alternative(html_body, "text/html")
            if LOGO_PATH.exists():
                logo = MIMEImage(LOGO_PATH.read_bytes())
                logo.add_header("Content-ID", "<event-logo>")
                logo.add_header("Content-Disposition", "inline", filename="logo.png")
                message.attach(logo)

        message.send(fail_silently=False)

        notification.status = Notification.Status.SENT
        notification.sent_at = timezone.now()
        notification.save(update_fields=["status", "sent_at", "updated_at"])

    except Exception as exc:  # noqa: BLE001 — log any failure rather than crash the caller
        notification.status = Notification.Status.FAILED
        notification.error_message = str(exc)
        notification.save(update_fields=["status", "error_message", "updated_at"])

    return notification
