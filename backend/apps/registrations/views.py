from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, IndividualRegistration, TeamRegistration
from .serializers import (
    CategorySerializer,
    PublicIndividualRegistrationCreateSerializer,
    PublicTeamRegistrationCreateSerializer,
    serialize_individual_record,
    serialize_team_record,
)
from .services import create_individual_registration, create_team_registration

# ---------------------------------------------------------------------------
# Individual registration
# ---------------------------------------------------------------------------


class PublicIndividualCategoryListView(APIView):
    """GET /api/v1/registrations/individual/categories/"""

    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.filter(entry_type=Category.EntryType.INDIVIDUAL, is_active=True)
        return Response(CategorySerializer(categories, many=True).data)


class PublicIndividualRegistrationCreateView(APIView):
    """POST /api/v1/registrations/individual/"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PublicIndividualRegistrationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration = create_individual_registration(**serializer.to_registration_kwargs())

        return Response(
            {
                "registrationId": registration.id,
                "reference": registration.registration_number,
                # A JSON number, not a DRF-style decimal string — the
                # frontend calls .toFixed() on this directly.
                "amount": float(registration.amount),
                "currency": registration.currency,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Team registration / roster
# ---------------------------------------------------------------------------


class PublicTeamCategoryListView(APIView):
    """GET /api/v1/registrations/team/categories/ — returns the one
    code="relay" row; the frontend looks it up by that code specifically
    (one fee covers the whole 8-runner team regardless of division)."""

    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.filter(entry_type=Category.EntryType.TEAM, is_active=True)
        return Response(CategorySerializer(categories, many=True).data)


class PublicTeamRegistrationCreateView(APIView):
    """POST /api/v1/registrations/team/ — creates the team and its roster."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PublicTeamRegistrationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        team = create_team_registration(**serializer.to_registration_kwargs())

        return Response(
            {
                "registrationId": team.id,
                "reference": team.registration_number,
                "amount": float(team.amount),
                "currency": team.currency,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Lookup ("track your registration")
# ---------------------------------------------------------------------------


class PublicRegistrationLookupView(APIView):
    """
    GET /api/v1/registrations/lookup/?q=<reference-or-email>

    Searches both individual and team registrations by reference number or
    email (participant email for an individual, captain email for a team).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()

        if not query:
            return Response(
                {"detail": "Provide a reference number or email as ?q="},
                status=status.HTTP_400_BAD_REQUEST,
            )

        individual = (
            IndividualRegistration.objects.select_related("participant", "category")
            .filter(registration_number__iexact=query)
            .first()
            or IndividualRegistration.objects.select_related("participant", "category")
            .filter(participant__email__iexact=query)
            .order_by("-registered_at")
            .first()
        )
        if individual:
            return Response(serialize_individual_record(individual))

        team = (
            TeamRegistration.objects.prefetch_related("roster")
            .filter(registration_number__iexact=query)
            .first()
            or TeamRegistration.objects.prefetch_related("roster")
            .filter(captain_email__iexact=query)
            .order_by("-registered_at")
            .first()
        )
        if team:
            return Response(serialize_team_record(team))

        return Response({"detail": "No matching registration found."}, status=status.HTTP_404_NOT_FOUND)
