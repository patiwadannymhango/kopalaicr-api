from rest_framework import serializers


class TeamCaptainLoginSerializer(serializers.Serializer):
    """Mirrors the frontend's loginTeamAccount(email, password) call."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
