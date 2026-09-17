from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.common.models import UUIDModel

from .managers import UserManager


class User(UUIDModel, AbstractBaseUser, PermissionsMixin):
    """
    Staff account — signs into both /django-admin/ (session auth) and the
    JWT admin API (apps.accounts) that backs the kopalaicr-admin
    dashboard SPA. is_staff gates every admin/* endpoint (see
    apps.common.permissions.IsStaffRole); there is no self-registration,
    only `createsuperuser` or an existing admin via /django-admin/.

    Registrants and team captains never authenticate through this model —
    the public registration/payment/lookup endpoints are open.
    """

    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
