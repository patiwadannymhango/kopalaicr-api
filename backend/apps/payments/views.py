import json

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import BaseRegistration

from .gateways.lipila.security import InvalidLipilaWebhook, verify_lipila_webhook
from .models import Payment, PaymentMethod
from .serializers import InitiatePaymentSerializer
from .services import apply_payment_outcome, create_payment, initiate_card_payment, initiate_mobile_payment, sync_payment_status


def _fail_payment(payment, exc):
    """
    Mark the payment FAILED (so it doesn't sit as a phantom PROCESSING row
    forever) and surface the gateway's actual reason to the caller instead
    of a generic 500.
    """

    payment.status = Payment.Status.FAILED
    payment.provider_response = {**payment.provider_response, "error": str(exc.args[0]) if exc.args else str(exc)}
    payment.save(update_fields=["status", "provider_response", "updated_at"])

    return Response({"detail": _gateway_error_message(exc)}, status=status.HTTP_502_BAD_GATEWAY)


def _gateway_error_message(exc):
    """Turn a raw gateway error payload into a message the registrant can act on."""

    payload = exc.args[0] if exc.args else {}

    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, dict) and errors:
            first_value = next(iter(errors.values()))
            if isinstance(first_value, list) and first_value:
                return str(first_value[0])
            return str(first_value)

        if payload.get("message"):
            return str(payload["message"])

    return "The payment provider rejected this request. Please check the details and try again."


def _find_target(registration_id):
    from apps.registrations.models import IndividualRegistration, RosterRunner, TeamRegistration

    return (
        IndividualRegistration.objects.filter(id=registration_id).first()
        or TeamRegistration.objects.filter(id=registration_id).first()
        or RosterRunner.objects.filter(id=registration_id).first()
    )


class PublicBankDetailsView(APIView):
    """GET /api/v1/payments/bank-details/"""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(settings.BANK_ACCOUNT_DETAILS)


class InitiatePaymentView(APIView):
    """
    POST /api/v1/payments/initiate/

    Shared by every payable thing in this project — an individual
    registration, a team's base entry, or one extra roster runner's fee —
    `registrationId` is looked up across all three (see _find_target), so
    the frontend doesn't need to say which kind it is.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InitiatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target = _find_target(data["registrationId"])

        if not target:
            return Response({"detail": "Registration not found."}, status=status.HTTP_404_NOT_FOUND)

        if target.status not in (BaseRegistration.Status.PENDING_PAYMENT, BaseRegistration.Status.PAYMENT_PROCESSING):
            return Response({"detail": "This registration cannot accept payment."}, status=status.HTTP_400_BAD_REQUEST)

        method = data["paymentMethod"]
        payment = create_payment(target=target, payment_method=method)

        redirect_url = ""

        callback_url = (
            f"{settings.PUBLIC_BASE_URL}/api/v1/payments/webhooks/lipila/"
            if settings.PUBLIC_BASE_URL
            else request.build_absolute_uri("/api/v1/payments/webhooks/lipila/")
        )

        if method in (PaymentMethod.MTN_MONEY, PaymentMethod.AIRTEL_MONEY, PaymentMethod.ZAMTEL_KWACHA):
            try:
                payment = initiate_mobile_payment(
                    payment=payment, phone_number=data["phoneNumber"], callback_url=callback_url
                )
            except Exception as exc:  # noqa: BLE001
                return _fail_payment(payment, exc)

        elif method == PaymentMethod.CARD:
            back_url = data.get("backUrl") or callback_url
            try:
                payment, redirect_url = initiate_card_payment(
                    payment=payment,
                    participant=target.contact,
                    city=data.get("city", ""),
                    address=data.get("address", ""),
                    zip_code=data.get("zipCode", ""),
                    country="ZM",
                    callback_url=callback_url,
                    back_url=back_url,
                )
            except Exception as exc:  # noqa: BLE001
                return _fail_payment(payment, exc)

        elif method == PaymentMethod.BANK_TRANSFER:
            # No gateway call — just record who to expect the transfer
            # from, so an admin can reconcile it against the bank
            # statement and mark it CONFIRMED manually. Kopala's frontend
            # doesn't actually drive this branch today (bank-transfer
            # registrations skip straight to "done" without calling
            # initiate — see IndividualRegistration.tsx/TeamRegistration.tsx),
            # but it's here for completeness / future admin tooling.
            payment.billing_details = {
                **payment.billing_details,
                "payer_name": data.get("payerName", ""),
                "transfer_reference": data.get("transferReference", ""),
            }
            payment.save(update_fields=["billing_details", "updated_at"])

        target.mark_processing()

        return Response(
            {
                "paymentId": payment.id,
                "status": payment.status,
                "redirectUrl": redirect_url,
            },
            status=status.HTTP_201_CREATED,
        )


class PublicPaymentStatusView(APIView):
    """
    GET /api/v1/payments/<payment_id>/status/

    Polled by the frontend while a mobile money prompt is on the
    registrant's phone (or while waiting on a card redirect). Each poll
    also actively re-checks the gateway rather than only trusting whatever
    a webhook has already written, so a delayed/dropped webhook doesn't
    leave this stuck reporting PROCESSING forever.
    """

    permission_classes = [AllowAny]

    def get(self, request, payment_id):
        try:
            payment = Payment.objects.select_related(
                "individual_registration", "team_registration", "roster_runner"
            ).get(id=payment_id)
        except Payment.DoesNotExist:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        payment = sync_payment_status(payment)
        target = payment.target

        return Response(
            {
                "status": payment.status,
                "registrationStatus": target.status,
                # Only set once the target reaches CONFIRMED (see
                # BaseRegistration.save()) — this is how the frontend picks
                # up the reference the moment it's actually assigned. Always
                # None for a roster-runner payment (see RosterRunner.registration_number).
                "reference": target.registration_number,
            }
        )


class LipilaWebhookView(APIView):
    """POST /api/v1/payments/webhooks/lipila/"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            verify_lipila_webhook(
                webhook_id=request.headers.get("webhook-id"),
                webhook_timestamp=request.headers.get("webhook-timestamp"),
                webhook_signature=request.headers.get("webhook-signature"),
                raw_body=request.body,
            )
        except InvalidLipilaWebhook:
            return Response({"detail": "Invalid webhook."}, status=status.HTTP_401_UNAUTHORIZED)

        data = json.loads(request.body)
        self._process(data)

        return Response({"status": "received"})

    def _process(self, data):
        """
        Per Lipila's docs, the payload is: referenceId, currency, amount,
        accountNumber, status ("Successful"/"Failed"), paymentType, type,
        identifier, message, externalId (optional), referenceData
        (optional) — the same shape for mobile money and card collections.
        `referenceId` and `referenceData` are both set to our own
        Payment.reference when creating the collection, so either one
        identifies the payment.
        """

        candidate_refs = [
            v
            for v in (
                data.get("referenceId"),
                data.get("identifier"),
                data.get("externalId"),
                data.get("referenceData"),
            )
            if v
        ]

        payment = None
        for ref in candidate_refs:
            payment = Payment.objects.filter(reference=ref).first() or Payment.objects.filter(
                provider_reference=ref
            ).first()
            if payment:
                break

        if not payment:
            return

        apply_payment_outcome(
            payment=payment, provider_status=data.get("status") or "", raw_response=data, response_key="webhook"
        )
