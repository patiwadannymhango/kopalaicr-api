from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "channel",
        "notification_type",
        "recipient",
        "status",
        "individual_registration",
        "team_registration",
        "created_at",
    )
    list_filter = ("channel", "notification_type", "status")
    search_fields = (
        "recipient",
        "individual_registration__registration_number",
        "team_registration__registration_number",
    )
    readonly_fields = (
        "individual_registration",
        "team_registration",
        "channel",
        "notification_type",
        "recipient",
        "subject",
        "body",
        "status",
        "error_message",
        "provider_response",
        "sent_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False
