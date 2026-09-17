from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from apps.common.models import BaseRegistration


def compute_dashboard_stats(*, registration_model, payment_field, entry_type):
    """
    Shared aggregation behind AdminIndividualDashboardView and
    AdminTeamDashboardView — same shape, scoped to one entry type's
    registrations and its own cash box (Withdrawal.entry_type), same as
    how each type gets its own table/filters/export on the admin
    dashboard.

    payment_field is "individual_registration" or "team_registration" —
    whichever Payment FK is set for this entry type (see
    apps.payments.models.Payment; exactly one of the two is ever set).

    Field meanings (see kopalaicr-admin's stat cards):
      revenue_confirmed — actually collected: Sum of SUCCESS payments.
        Deliberately NOT Sum(amount) over CONFIRMED registrations — a
        registration can reach CONFIRMED with no successful Payment
        behind it (e.g. an admin flips status without recording cash),
        which wouldn't be real revenue. Every CONFIRMED registration
        created/edited through the admin API is backed by a Payment (see
        apps.payments.services.create_admin_cash_payment), so this stays
        accurate regardless of path.
      revenue_pending — owed: Sum(amount) over still-unpaid registrations.
      revenue_today — revenue_confirmed's slice for payments settled today.
      total_income — Sum(amount) over every non-cancelled/expired
        registration regardless of payment status: what the event could
        earn if every pending one also paid.
      cash_withdrawn / cash_available — see apps.payments.models.Withdrawal.
    """

    registrations = registration_model.objects.all()
    today = timezone.localdate()

    from apps.payments.models import Payment, Withdrawal

    by_status = list(registrations.values("status").annotate(count=Count("id")))
    today_count = registrations.filter(registered_at__date=today).count()

    payments = Payment.objects.filter(**{f"{payment_field}__isnull": False}, status=Payment.Status.SUCCESS)

    revenue_confirmed = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    revenue_today = payments.filter(paid_at__date=today).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    revenue_pending = (
        registrations.filter(
            status__in=[BaseRegistration.Status.PENDING_PAYMENT, BaseRegistration.Status.PAYMENT_PROCESSING]
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    total_income = (
        registrations.exclude(
            status__in=[BaseRegistration.Status.CANCELLED, BaseRegistration.Status.EXPIRED]
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    cash_withdrawn = (
        Withdrawal.objects.filter(entry_type=entry_type).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    )
    cash_available = revenue_confirmed - cash_withdrawn

    return {
        "total_registrations": registrations.count(),
        "today_count": today_count,
        "by_status": by_status,
        "revenue_confirmed": str(revenue_confirmed),
        "revenue_pending": str(revenue_pending),
        "revenue_today": str(revenue_today),
        "total_income": str(total_income),
        "cash_withdrawn": str(cash_withdrawn),
        "cash_available": str(cash_available),
    }
