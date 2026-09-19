from rest_framework import serializers

from .models import Notification


class AdminNotificationSerializer(serializers.ModelSerializer):
    registration_number = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "channel",
            "notification_type",
            "recipient",
            "subject",
            "status",
            "error_message",
            "registration_number",
            "created_at",
            "sent_at",
        )

    def get_registration_number(self, obj):
        target = obj.individual_registration or obj.team_registration or obj.vendor_registration
        return target.registration_number if target else None
