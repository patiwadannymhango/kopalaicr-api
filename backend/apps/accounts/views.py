from rest_framework import filters, status
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common.permissions import IsSuperuserRole

from .models import User
from .serializers import AdminUserCreateSerializer, AdminUserUpdateSerializer, LoginSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — email + password, staff accounts only."""

    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class MeView(APIView):
    """GET /api/v1/auth/me/ — the signed-in admin's own profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ---------------------------------------------------------------------------
# Admin-facing — staff account management (superuser-only, see
# apps.common.permissions.IsSuperuserRole)
# ---------------------------------------------------------------------------


class AdminUserListView(ListAPIView):
    """GET /api/v1/auth/admin/users/ — supports ?search= (name/email)."""

    permission_classes = [IsSuperuserRole]
    serializer_class = UserSerializer
    queryset = User.objects.all().order_by("first_name", "last_name")
    filter_backends = [filters.SearchFilter]
    search_fields = ["email", "first_name", "last_name"]
    pagination_class = None


class AdminUserCreateView(APIView):
    """POST /api/v1/auth/admin/users/create/ — new account always signs
    in with is_staff=True (see AdminUserCreateSerializer)."""

    permission_classes = [IsSuperuserRole]

    def post(self, request):
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class AdminUserDetailView(RetrieveUpdateAPIView):
    """
    GET   — full profile.
    PATCH — edit name/phone, or toggle is_active/is_staff/is_superuser.
    Refuses to let a superuser deactivate or demote their own account —
    is_active also gates /django-admin/ session login, so there'd be no
    way back in without another superuser already on hand.
    """

    permission_classes = [IsSuperuserRole]
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def patch(self, request, *args, **kwargs):
        user = self.get_object()

        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if user.id == request.user.id:
            locking_out = data.get("is_active") is False or data.get("is_superuser") is False
            if locking_out:
                return Response(
                    {"detail": "You can't deactivate or demote your own account."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer.save()
        return Response(UserSerializer(user).data)
