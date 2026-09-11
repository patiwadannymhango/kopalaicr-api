from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "individual_registration",
        "team_registration",
        "roster_runner",
        "amount",
        "currency",
        "status",
        "payment_method",
        "created_at",
    )
    list_filter = ("status", "payment_method")
    search_fields = (
        "reference",
        "provider_reference",
        "individual_registration__registration_number",
        "team_registration__registration_number",
        "roster_runner__full_name",
    )
    autocomplete_fields = ("individual_registration", "team_registration", "roster_runner")
    readonly_fields = ("reference", "provider_reference", "provider_response", "created_at", "updated_at")
