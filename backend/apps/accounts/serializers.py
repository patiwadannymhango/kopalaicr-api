from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "is_staff",
            "is_superuser",
            "is_active",
        )


class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone", "password", "is_superuser")

    def create(self, validated_data):
        password = validated_data.pop("password")
        # Every account created here signs into this admin dashboard, so
        # is_staff is always on regardless of what the caller sent.
        user = User(**validated_data, is_staff=True)
        user.set_password(password)
        user.save()
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """PATCH body for apps.accounts.views.AdminUserDetailView — every
    field optional (the view passes partial=True)."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "is_active", "is_staff", "is_superuser")


class LoginSerializer(TokenObtainPairSerializer):
    """Only a staff account can sign into the admin dashboard — a runner
    or team captain never has one (see apps.accounts.models.User)."""

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_staff:
            raise serializers.ValidationError("This account does not have admin access.")
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["full_name"] = user.full_name
        return token
