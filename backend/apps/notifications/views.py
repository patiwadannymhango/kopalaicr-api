from rest_framework import filters, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsStaffRole

from .email import send_email
from .models import Notification
from .serializers import AdminNotificationSerializer


class AdminNotificationListView(ListAPIView):
    """
    GET /api/v1/notifications/admin/

    Delivery log for every email/SMS this event has attempted to send.
    Supports ?search= (recipient/subject/reference), ?status=,
    ?channel=, ?notification_type= and standard pagination.
    """

    permission_classes = [IsStaffRole]
    serializer_class = AdminNotificationSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "recipient",
        "subject",
        "individual_registration__registration_number",
        "team_registration__registration_number",
        "vendor_registration__registration_number",
    ]
    ordering_fields = ["created_at", "status"]

    def get_queryset(self):
        qs = Notification.objects.select_related(
            "individual_registration", "team_registration", "vendor_registration"
        )
        params = self.request.query_params

        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("channel"):
            qs = qs.filter(channel=params["channel"])
        if params.get("notification_type"):
            qs = qs.filter(notification_type=params["notification_type"])

        return qs


class AdminNotificationResendView(APIView):
    """
    POST /api/v1/notifications/admin/<uuid:pk>/resend/
    Body: {"recipient": "someone@example.com"}

    Email only — re-sends the notification's stored plain-text body (the
    original HTML template isn't persisted, so a resend is plain text)
    to whatever address is given, logging a fresh Notification row like
    any other send (see apps.notifications.email.send_email).
    """

    permission_classes = [IsStaffRole]

    def post(self, request, pk):
        try:
            original = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if original.channel != Notification.Channel.EMAIL:
            return Response(
                {"detail": "Only email notifications can be resent."}, status=status.HTTP_400_BAD_REQUEST
            )

        recipient = (request.data.get("recipient") or "").strip()
        if not recipient:
            return Response({"detail": "recipient is required."}, status=status.HTTP_400_BAD_REQUEST)

        target = original.individual_registration or original.team_registration or original.vendor_registration

        notification = send_email(
            to=recipient,
            subject=original.subject,
            text_body=original.body,
            target=target,
            notification_type=original.notification_type,
        )

        return Response(AdminNotificationSerializer(notification).data, status=status.HTTP_201_CREATED)
