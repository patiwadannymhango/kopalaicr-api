from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AdminUserCreateView, AdminUserDetailView, AdminUserListView, LoginView, MeView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/create/", AdminUserCreateView.as_view(), name="admin-user-create"),
    path("admin/users/<uuid:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
]
