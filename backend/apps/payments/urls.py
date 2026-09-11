from django.urls import path

from .views import InitiatePaymentView, LipilaWebhookView, PublicBankDetailsView, PublicPaymentStatusView

urlpatterns = [
    path("bank-details/", PublicBankDetailsView.as_view(), name="payments-bank-details"),
    path("initiate/", InitiatePaymentView.as_view(), name="payments-initiate"),
    path("<uuid:payment_id>/status/", PublicPaymentStatusView.as_view(), name="payments-status"),
    path("webhooks/lipila/", LipilaWebhookView.as_view(), name="payments-webhook-lipila"),
]
