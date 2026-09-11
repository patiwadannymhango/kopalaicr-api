from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TeamCaptainLoginSerializer


class TeamCaptainLoginView(APIView):
    """
    POST /api/v1/auth/team/login/

    The only account type that authenticates in this backend — mirrors
    apps.registrations.services.create_team_registration, which creates
    this same auth_token at registration time so the frontend never needs
    a separate "log in right after registering" step. See
    apps.registrations.auth for how this token is verified on subsequent
    requests.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        from apps.registrations.models import TeamRegistration

        serializer = TeamCaptainLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        team = TeamRegistration.objects.filter(captain_email__iexact=email).first()

        if not team or not team.check_password(password):
            return Response({"detail": "Incorrect email or password."}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({"authToken": team.auth_token})
