from rest_framework.permissions import BasePermission


class IsStaffRole(BasePermission):
    """
    Gate for every admin endpoint (apps.accounts, apps.registrations
    admin/* views, apps.payments admin/* views) — the dashboard SPA at
    kopalaicr-admin is the only thing that authenticates as this User
    model, so is_staff alone is enough; there's no separate read-only
    role to distinguish (unlike the Kabwe reference this project follows
    for its other admin-API patterns).
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
