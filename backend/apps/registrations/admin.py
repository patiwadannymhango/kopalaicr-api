from django.contrib import admin

from apps.common.models import BaseRegistration

from .models import Category, IndividualRegistration, Participant, RosterRunner, TeamRegistration, VendorRegistration


class ConfirmOnSaveAdminMixin:
    """
    Firing the confirmation email/SMS on a payment succeeding is handled
    by apps.payments.services.apply_payment_outcome (BaseRegistration.confirm_payment).
    This mixin makes manually flipping `status` to CONFIRMED in
    /django-admin/ (e.g. reconciling a bank transfer) behave the same way,
    so that's a real substitute for the admin REST API this project isn't
    building — see the project README.
    """

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = type(obj).objects.filter(pk=obj.pk).values_list("status", flat=True).first()

        super().save_model(request, obj, form, change)

        if obj.status == BaseRegistration.Status.CONFIRMED and old_status != BaseRegistration.Status.CONFIRMED:
            obj.notify_confirmed()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "entry_type", "price", "currency", "capacity", "is_active")
    list_editable = ("price", "is_active")
    list_filter = ("entry_type", "is_active")
    search_fields = ("name", "code")


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "gender", "age_range")
    search_fields = ("full_name", "email", "phone")


@admin.register(IndividualRegistration)
class IndividualRegistrationAdmin(ConfirmOnSaveAdminMixin, admin.ModelAdmin):
    list_display = (
        "registration_number",
        "participant",
        "category",
        "status",
        "amount",
        "currency",
        "registered_at",
    )
    list_filter = ("status", "category")
    search_fields = (
        "registration_number",
        "participant__full_name",
        "participant__email",
        "participant__phone",
    )
    autocomplete_fields = ("participant", "category")
    readonly_fields = ("registration_number", "registered_at", "updated_at")


class RosterRunnerInline(admin.TabularInline):
    model = RosterRunner
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(RosterRunner)
class RosterRunnerAdmin(admin.ModelAdmin):
    # Day-to-day roster editing happens via the TeamRegistration inline
    # above; this is mainly for searching/browsing runners across teams.
    list_display = ("full_name", "team_registration", "gender")
    search_fields = ("full_name", "team_registration__team_name")
    autocomplete_fields = ("team_registration",)


@admin.register(TeamRegistration)
class TeamRegistrationAdmin(ConfirmOnSaveAdminMixin, admin.ModelAdmin):
    list_display = (
        "registration_number",
        "team_name",
        "company_or_institution",
        "relay_category",
        "captain_email",
        "status",
        "amount",
        "currency",
        "registered_at",
    )
    list_filter = ("status", "relay_category")
    search_fields = ("registration_number", "team_name", "company_or_institution", "captain_email", "captain_phone")
    autocomplete_fields = ("category",)
    readonly_fields = ("registration_number", "registered_at", "updated_at")
    inlines = [RosterRunnerInline]


@admin.register(VendorRegistration)
class VendorRegistrationAdmin(ConfirmOnSaveAdminMixin, admin.ModelAdmin):
    list_display = (
        "registration_number",
        "business_name",
        "contact_person",
        "category",
        "status",
        "amount",
        "currency",
        "registered_at",
    )
    list_filter = ("status", "category", "requirement")
    search_fields = ("registration_number", "business_name", "contact_person", "contact_email", "contact_phone")
    autocomplete_fields = ("category",)
    readonly_fields = ("registration_number", "registered_at", "updated_at")


admin.site.site_header = "Kopala ICR 2026"
admin.site.site_title = "Kopala ICR Admin"
admin.site.index_title = "Event administration"
