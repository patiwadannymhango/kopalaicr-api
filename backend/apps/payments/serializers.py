from decimal import Decimal

from rest_framework import serializers

from .models import PaymentMethod, Withdrawal


class InitiatePaymentSerializer(serializers.Serializer):
    """Mirrors the frontend's InitiatePaymentParams shape exactly.
    `registrationId` is looked up across IndividualRegistration and
    TeamRegistration (see InitiatePaymentView) — their UUIDs never collide
    in practice, so the frontend doesn't need to say which kind of target
    it's paying for."""

    registrationId = serializers.UUIDField()
    paymentMethod = serializers.ChoiceField(choices=PaymentMethod.choices)

    phoneNumber = serializers.CharField(required=False, allow_blank=True)

    # Card only
    city = serializers.CharField(required=False, allow_blank=True, max_length=100)
    address = serializers.CharField(required=False, allow_blank=True, max_length=255)
    zipCode = serializers.CharField(required=False, allow_blank=True, max_length=20)
    backUrl = serializers.URLField(required=False, allow_blank=True)

    # Bank transfer only
    payerName = serializers.CharField(required=False, allow_blank=True, max_length=150)
    transferReference = serializers.CharField(required=False, allow_blank=True, max_length=100)

    def validate(self, attrs):
        method = attrs["paymentMethod"]

        if method in (PaymentMethod.MTN_MONEY, PaymentMethod.AIRTEL_MONEY, PaymentMethod.ZAMTEL_KWACHA):
            if not attrs.get("phoneNumber"):
                raise serializers.ValidationError(
                    {"phoneNumber": "Phone number is required for mobile money payments."}
                )

        if method == PaymentMethod.CARD:
            missing = {
                field: "This field is required for card payments."
                for field in ("city", "address", "zipCode")
                if not attrs.get(field)
            }
            if missing:
                raise serializers.ValidationError(missing)

        if method == PaymentMethod.BANK_TRANSFER and not attrs.get("payerName"):
            raise serializers.ValidationError(
                {"payerName": "Please provide the name the transfer will be made from."}
            )

        return attrs


# ---------------------------------------------------------------------------
# Admin-facing — cash withdrawals
# ---------------------------------------------------------------------------


class AdminWithdrawalSerializer(serializers.ModelSerializer):
    withdrawn_by_name = serializers.CharField(source="withdrawn_by.full_name", read_only=True, default="")

    class Meta:
        model = Withdrawal
        fields = (
            "id",
            "entry_type",
            "amount",
            "currency",
            "narration",
            "withdrawn_by_name",
            "withdrawn_at",
        )
        read_only_fields = ("id", "currency", "withdrawn_by_name", "withdrawn_at")


class AdminWithdrawalCreateSerializer(serializers.Serializer):
    entry_type = serializers.ChoiceField(choices=Withdrawal._meta.get_field("entry_type").choices)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    narration = serializers.CharField(required=False, allow_blank=True, max_length=255)
