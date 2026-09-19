from django.urls import path

from .views import AdminNotificationListView, AdminNotificationResendView

urlpatterns = [
    path("admin/", AdminNotificationListView.as_view(), name="admin-notification-list"),
    path("admin/<uuid:pk>/resend/", AdminNotificationResendView.as_view(), name="admin-notification-resend"),
]
