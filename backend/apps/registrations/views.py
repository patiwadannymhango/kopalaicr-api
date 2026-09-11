from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import CaptainTokenAuthentication, IsTeamCaptain
from .models import Category, IndividualRegistration, TeamRegistration
from .serializers import (
    CategorySerializer,
    PublicIndividualRegistrationCreateSerializer,
    PublicTeamRegistrationCreateSerializer,
    RunnerRosterEntrySerializer,
    TeamAccountSerializer,
    serialize_individual_record,
    serialize_team_record,
)
from .services import add_roster_runner, create_individual_registration, create_team_registration

# ---------------------------------------------------------------------------
# Individual registration
# ---------------------------------------------------------------------------


class PublicIndividualCategoryListView(APIView):
    """GET /api/v1/registrations/individual/categories/"""

    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.filter(
            entry_type=Category.EntryType.INDIVIDUAL, is_extra_fee=False, is_active=True
        )
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
        categories = Category.objects.filter(
            entry_type=Category.EntryType.TEAM, is_extra_fee=False, is_active=True
        )
        return Response(CategorySerializer(categories, many=True).data)


class PublicExtraRunnerFeeView(APIView):
    """GET /api/v1/registrations/team/extra-runner-fee/"""

    permission_classes = [AllowAny]

    def get(self, request):
        category = Category.objects.filter(
            code="extra-runner", entry_type=Category.EntryType.TEAM, is_active=True
        ).first()

        if not category:
            return Response({"price": 0})

        return Response({"price": float(category.price)})


class PublicTeamRegistrationCreateView(APIView):
    """POST /api/v1/registrations/team/ — creates the team, its roster, and
    the captain's login account (auth_token) in one call."""

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
                "authToken": team.auth_token,
            },
            status=status.HTTP_201_CREATED,
        )


class TeamMeView(APIView):
    """GET /api/v1/team/me/ — the logged-in captain's own team account."""

    authentication_classes = [CaptainTokenAuthentication]
    permission_classes = [IsTeamCaptain]

    def get(self, request):
        return Response(TeamAccountSerializer(request.auth).data)


class TeamRosterAddView(APIView):
    """POST /api/v1/team/me/roster/ — adds one runner to the logged-in
    team's roster; the backend (not the caller) decides whether this seat
    is free or chargeable."""

    authentication_classes = [CaptainTokenAuthentication]
    permission_classes = [IsTeamCaptain]

    def post(self, request):
        team = request.auth

        if team.status != TeamRegistration.Status.CONFIRMED:
            return Response(
                {"detail": "Pay your team's entry fee before adding runners."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RunnerRosterEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        runner, extra_fee_category = add_roster_runner(
            team=team, full_name=data["fullName"], gender=data.get("gender", "")
        )

        return Response(
            {
                "runnerId": runner.id,
                "confirmed": runner.covered,
                "paymentRequired": not runner.covered,
                "amount": float(extra_fee_category.price) if extra_fee_category else None,
                "currency": extra_fee_category.currency if extra_fee_category else "ZMW",
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
