from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.permissions import BasePermission

from .models import TeamRegistration


class CaptainTokenAuthentication(BaseAuthentication):
    """
    Verifies the opaque bearer token a team captain's browser sends
    (src/api/http.ts: `Authorization: Bearer <token>`) against
    TeamRegistration.auth_token.

    Deliberately not JWT and not tied into Django's own auth system: a
    team isn't a `User` (see apps.accounts.models.User's docstring) and
    there's exactly one thing to check per request, a straight token
    lookup. The authenticated team lands on `request.auth`, not
    `request.user` — `request.user` stays AnonymousUser so this can never
    be confused with a Django-admin session. Only declared explicitly on
    the two team-account views (apps.registrations.views); nothing global
    changes.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        header = get_authorization_header(request).decode("utf-8", errors="ignore")
        if not header or not header.startswith(f"{self.keyword} "):
            return None

        token = header[len(self.keyword) + 1 :].strip()
        if not token:
            return None

        team = TeamRegistration.objects.filter(auth_token=token).first()
        if not team:
            return None

        return (AnonymousUser(), team)


class IsTeamCaptain(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, TeamRegistration)
