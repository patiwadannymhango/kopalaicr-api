from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.common.models import UUIDModel

from .managers import UserManager


class User(UUIDModel, AbstractBaseUser, PermissionsMixin):
    """
    Django-admin account (/django-admin/ only — there is no JWT/REST admin
    API in this project, see README). There is no self-registration; the
    first (and so far only) account is made with `createsuperuser`.

    Registrants and team captains never authenticate through this model —
    the public registration/payment/lookup endpoints are open, and team
    captains use their own opaque token (see apps.registrations.auth).
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
