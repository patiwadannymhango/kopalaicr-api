import csv
import io

import openpyxl
from django.http import HttpResponse
from openpyxl.utils import get_column_letter
from rest_framework import filters, status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsStaffRole
from apps.payments.services import create_admin_cash_payment

from .admin_dashboard import compute_dashboard_stats
from .models import Category, IndividualRegistration, Participant, TeamRegistration
from .serializers import (
    AdminIndividualRegistrationSerializer,
    AdminIndividualRegistrationUpdateSerializer,
    AdminManualIndividualRegistrationSerializer,
    AdminManualTeamRegistrationSerializer,
    AdminTeamRegistrationSerializer,
    AdminTeamRegistrationUpdateSerializer,
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


# ---------------------------------------------------------------------------
# Admin-facing — Individual
# ---------------------------------------------------------------------------


class AdminIndividualDashboardView(APIView):
    """GET /api/v1/registrations/admin/individual/dashboard/"""

    permission_classes = [IsAuthenticated, IsStaffRole]

    def get(self, request):
        return Response(
            compute_dashboard_stats(
                registration_model=IndividualRegistration,
                payment_field="individual_registration",
                entry_type="INDIVIDUAL",
            )
        )


class AdminIndividualFilterOptionsView(APIView):
    """GET /api/v1/registrations/admin/individual/filters/"""

    permission_classes = [IsAuthenticated, IsStaffRole]

    def get(self, request):
        categories = Category.objects.filter(entry_type=Category.EntryType.INDIVIDUAL, is_active=True)
        organisations = list(
            IndividualRegistration.objects.exclude(club_or_institution="")
            .order_by("club_or_institution")
            .values_list("club_or_institution", flat=True)
            .distinct()
        )
        return Response(
            {
                "categories": CategorySerializer(categories, many=True).data,
                "genders": [g.value for g in Participant.Gender],
                "organisations": organisations,
            }
        )


class AdminIndividualRegistrationListView(ListAPIView):
    """
    GET /api/v1/registrations/admin/individual/registrations/

    Supports ?search=, ?status=, ?category=, ?gender=, ?organisation=,
    ?ordering= and standard pagination.
    """

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class = AdminIndividualRegistrationSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["registration_number", "participant__full_name", "participant__email", "participant__phone"]
    ordering_fields = ["registered_at", "amount", "status"]

    def get_queryset(self):
        qs = IndividualRegistration.objects.select_related("participant", "category")
        params = self.request.query_params

        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("category"):
            qs = qs.filter(category_id=params["category"])
        if params.get("gender"):
            qs = qs.filter(participant__gender=params["gender"])
        if params.get("organisation"):
            qs = qs.filter(club_or_institution=params["organisation"])

        return qs


class AdminIndividualRegistrationDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET    — any signed-in admin.
    PATCH  — partial update (participant and/or registration fields).
    Flipping `status` to CONFIRMED without an existing successful
    Payment records one for the amount under `payment_method` (default
    CASH) so the dashboard's revenue figures stay accurate, and notifies
    the runner exactly like an online payment would.
    DELETE — removes the registration and any payments against it.
    """

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class = AdminIndividualRegistrationSerializer
    queryset = IndividualRegistration.objects.select_related("participant", "category")

    def perform_destroy(self, instance):
        instance.payments.all().delete()
        instance.delete()

    def patch(self, request, *args, **kwargs):
        registration = self.get_object()

        serializer = AdminIndividualRegistrationUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        participant_updates = {
            k: v for k, v in data.items() if k in AdminIndividualRegistrationUpdateSerializer.PARTICIPANT_FIELDS
        }
        registration_updates = {
            k: v for k, v in data.items() if k not in AdminIndividualRegistrationUpdateSerializer.PARTICIPANT_FIELDS
        }

        if participant_updates:
            for field, value in participant_updates.items():
                setattr(registration.participant, field, value)
            registration.participant.save(update_fields=[*participant_updates.keys()])

        old_status = registration.status
        new_status = registration_updates.get("status")

        if registration_updates:
            for field, value in registration_updates.items():
                setattr(registration, field, value)
            registration.save(update_fields=[*registration_updates.keys(), "updated_at"])

        if new_status == IndividualRegistration.Status.CONFIRMED and old_status != new_status:
            from apps.payments.models import Payment

            if not registration.payments.filter(status=Payment.Status.SUCCESS).exists():
                create_admin_cash_payment(target=registration)

            registration.notify_confirmed()

        return Response(AdminIndividualRegistrationSerializer(registration).data)


class AdminIndividualRegistrationCreateView(APIView):
    """
    POST /api/v1/registrations/admin/individual/registrations/create/

    Manual "Add person" — walk-in/phone registration. Defaults to
    CONFIRMED, recording a matching cash/EFT Payment (see
    apps.payments.services.create_admin_cash_payment) so it counts
    towards revenue collected exactly like an online payment would.
    """

    permission_classes = [IsAuthenticated, IsStaffRole]

    def post(self, request):
        serializer = AdminManualIndividualRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment_method = serializer.validated_data.get("payment_method") or "CASH"

        registration = create_individual_registration(**serializer.to_registration_kwargs())

        if registration.status == IndividualRegistration.Status.CONFIRMED:
            create_admin_cash_payment(target=registration, payment_method=payment_method)

        return Response(AdminIndividualRegistrationSerializer(registration).data, status=status.HTTP_201_CREATED)


class AdminIndividualBulkUploadTemplateView(APIView):
    """GET /api/v1/registrations/admin/individual/registrations/bulk-upload/template/"""

    permission_classes = [IsAuthenticated, IsStaffRole]

    COLUMNS = [
        "full_name",
        "email",
        "phone",
        "category_code",
        "status",
        "gender",
        "age_range",
        "country",
        "t_shirt_size",
        "division",
        "town_or_city",
        "club_or_institution",
        "emergency_contact_name",
        "emergency_contact_phone",
        "medical_notes",
    ]

    def get(self, request):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Template"

        for col_index, header in enumerate(self.COLUMNS, start=1):
            sheet.cell(row=1, column=col_index, value=header)
        for col_index in range(1, len(self.COLUMNS) + 1):
            sheet.column_dimensions[get_column_letter(col_index)].width = 22

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="individual-bulk-upload-template.xlsx"'
        return response


class AdminIndividualBulkUploadView(APIView):
    """
    POST /api/v1/registrations/admin/individual/registrations/bulk-upload/

    Accepts a CSV or XLSX (multipart field "file") with columns
    full_name, category_code (required) plus the rest of the manual "Add
    person" fields. Creates what it can and reports the rest — one bad
    row never fails the whole batch.
    """

    permission_classes = [IsAuthenticated, IsStaffRole]
    parser_classes = [MultiPartParser]

    REQUIRED_COLUMNS = ["full_name", "category_code"]

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "Attach a file under the 'file' field."}, status=status.HTTP_400_BAD_REQUEST)

        rows = self._parse_rows(upload)
        categories = {c.code: c for c in Category.objects.filter(entry_type=Category.EntryType.INDIVIDUAL)}

        created = []
        errors = []

        for index, row in enumerate(rows, start=2):  # header is row 1
            missing = [c for c in self.REQUIRED_COLUMNS if not row.get(c)]
            if missing:
                errors.append({"row": index, "error": f"Missing: {', '.join(missing)}"})
                continue

            category = categories.get(row["category_code"])
            if not category:
                errors.append({"row": index, "error": f"Unknown category_code '{row['category_code']}'"})
                continue

            desired_status = (row.get("status") or "CONFIRMED").upper()
            if desired_status not in IndividualRegistration.Status.values:
                errors.append({"row": index, "error": f"Unknown status '{desired_status}'"})
                continue

            try:
                registration = create_individual_registration(
                    category=category,
                    participant_data={
                        "full_name": row["full_name"],
                        "email": row.get("email", ""),
                        "phone": row.get("phone", ""),
                        "gender": row.get("gender", ""),
                        "age_range": row.get("age_range", ""),
                        "country": row.get("country", ""),
                    },
                    details={
                        "t_shirt_size": row.get("t_shirt_size", ""),
                        "division": row.get("division", ""),
                        "town_or_city": row.get("town_or_city", ""),
                        "club_or_institution": row.get("club_or_institution", ""),
                        "emergency_contact_name": row.get("emergency_contact_name", ""),
                        "emergency_contact_phone": row.get("emergency_contact_phone", ""),
                        "medical_notes": row.get("medical_notes", ""),
                        "accepted_terms": True,
                    },
                    status=desired_status,
                )

                if registration.status == IndividualRegistration.Status.CONFIRMED:
                    create_admin_cash_payment(target=registration)

                created.append(registration.registration_number or f"(pending) {registration.id}")

            except Exception as exc:  # noqa: BLE001
                errors.append({"row": index, "error": str(exc)})

        return Response(
            {
                "created_count": len(created),
                "created_references": created,
                "error_count": len(errors),
                "errors": errors,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST,
        )

    def _parse_rows(self, upload):
        filename = (upload.name or "").lower()

        if filename.endswith(".csv"):
            text = upload.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            return [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in reader]

        workbook = openpyxl.load_workbook(upload, data_only=True)
        sheet = workbook.active

        rows_iter = sheet.iter_rows(values_only=True)
        headers = [str(h or "").strip().lower() for h in next(rows_iter)]

        rows = []
        for values in rows_iter:
            if all(v in (None, "") for v in values):
                continue
            row = {headers[i]: ("" if v is None else str(v).strip()) for i, v in enumerate(values) if i < len(headers)}
            rows.append(row)

        return rows


class AdminIndividualExportView(APIView):
    """GET /api/v1/registrations/admin/individual/registrations/export/ — streams an .xlsx."""

    permission_classes = [IsAuthenticated, IsStaffRole]

    COLUMNS = [
        ("Reference", lambda r: r.registration_number),
        ("Status", lambda r: r.status),
        ("Full name", lambda r: r.participant.full_name),
        ("Email", lambda r: r.participant.email),
        ("Phone", lambda r: r.participant.phone),
        ("Gender", lambda r: r.participant.gender),
        ("Age range", lambda r: r.participant.age_range),
        ("Category", lambda r: r.category.name),
        ("T-shirt size", lambda r: r.t_shirt_size),
        ("Division", lambda r: r.division),
        ("Town/City", lambda r: r.town_or_city),
        ("Club/Institution", lambda r: r.club_or_institution),
        ("Emergency contact", lambda r: r.emergency_contact_name),
        ("Emergency phone", lambda r: r.emergency_contact_phone),
        ("Amount", lambda r: float(r.amount)),
        ("Currency", lambda r: r.currency),
        ("Registered at", lambda r: r.registered_at.replace(tzinfo=None) if r.registered_at else None),
    ]

    def get(self, request):
        registrations = IndividualRegistration.objects.select_related("participant", "category").order_by(
            "-registered_at"
        )

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Individual registrations"

        for col_index, (header, _) in enumerate(self.COLUMNS, start=1):
            sheet.cell(row=1, column=col_index, value=header)

        for row_index, registration in enumerate(registrations, start=2):
            for col_index, (_, getter) in enumerate(self.COLUMNS, start=1):
                sheet.cell(row=row_index, column=col_index, value=getter(registration))

        for col_index in range(1, len(self.COLUMNS) + 1):
            sheet.column_dimensions[get_column_letter(col_index)].width = 22

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="kopala-icr-individual-registrations.xlsx"'
        return response


# ---------------------------------------------------------------------------
# Admin-facing — Team
# ---------------------------------------------------------------------------


class AdminTeamDashboardView(APIView):
    """GET /api/v1/registrations/admin/team/dashboard/"""

    permission_classes = [IsAuthenticated, IsStaffRole]

    def get(self, request):
        return Response(
            compute_dashboard_stats(
                registration_model=TeamRegistration,
                payment_field="team_registration",
                entry_type="TEAM",
            )
        )


class AdminTeamFilterOptionsView(APIView):
    """GET /api/v1/registrations/admin/team/filters/"""

    permission_classes = [IsAuthenticated, IsStaffRole]

    def get(self, request):
        categories = Category.objects.filter(entry_type=Category.EntryType.TEAM, is_active=True)
        return Response(
            {
                "categories": CategorySerializer(categories, many=True).data,
                "relay_categories": [c.value for c in TeamRegistration.RelayCategory],
            }
        )


class AdminTeamRegistrationListView(ListAPIView):
    """
    GET /api/v1/registrations/admin/team/registrations/

    Supports ?search=, ?status=, ?category=, ?relay_category=,
    ?ordering= and standard pagination.
    """

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class = AdminTeamRegistrationSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "registration_number",
        "team_name",
        "company_or_institution",
        "captain_first_name",
        "captain_last_name",
        "captain_email",
        "captain_phone",
    ]
    ordering_fields = ["registered_at", "amount", "status"]

    def get_queryset(self):
        qs = TeamRegistration.objects.select_related("category").prefetch_related("roster")
        params = self.request.query_params

        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("category"):
            qs = qs.filter(category_id=params["category"])
        if params.get("relay_category"):
            qs = qs.filter(relay_category=params["relay_category"])

        return qs


class AdminTeamRegistrationDetailView(RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE — same rules as AdminIndividualRegistrationDetailView,
    minus roster editing (stays Django-admin-only — see the README and
    AdminTeamRegistrationUpdateSerializer's docstring).
    """

    permission_classes = [IsAuthenticated, IsStaffRole]
    serializer_class = AdminTeamRegistrationSerializer
    queryset = TeamRegistration.objects.select_related("category").prefetch_related("roster")

    def perform_destroy(self, instance):
        instance.payments.all().delete()
        instance.delete()

    def patch(self, request, *args, **kwargs):
        team = self.get_object()

        serializer = AdminTeamRegistrationUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        old_status = team.status
        new_status = data.get("status")

        if data:
            for field, value in data.items():
                setattr(team, field, value)
            team.save(update_fields=[*data.keys(), "updated_at"])

        if new_status == TeamRegistration.Status.CONFIRMED and old_status != new_status:
            from apps.payments.models import Payment

            if not team.payments.filter(status=Payment.Status.SUCCESS).exists():
                create_admin_cash_payment(target=team)

            team.notify_confirmed()

        return Response(AdminTeamRegistrationSerializer(team).data)


class AdminTeamRegistrationCreateView(APIView):
    """
    POST /api/v1/registrations/admin/team/registrations/create/

    Manual "Add team" — same cash-payment-on-CONFIRMED behaviour as
    AdminIndividualRegistrationCreateView. create_team_registration()
    itself has no `status` parameter (the public flow always starts
    PENDING_PAYMENT), so the desired status is applied as a second save
    here rather than changing that shared service function's signature.
    """

    permission_classes = [IsAuthenticated, IsStaffRole]

    def post(self, request):
        serializer = AdminManualTeamRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        desired_status = serializer.validated_data["status"]
        payment_method = serializer.validated_data.get("payment_method") or "CASH"

        team = create_team_registration(**serializer.to_registration_kwargs())

        if desired_status != team.status:
            team.status = desired_status
            team.save(update_fields=["status", "updated_at"])

        if team.status == TeamRegistration.Status.CONFIRMED:
            create_admin_cash_payment(target=team, payment_method=payment_method)

        return Response(AdminTeamRegistrationSerializer(team).data, status=status.HTTP_201_CREATED)


class AdminTeamExportView(APIView):
    """GET /api/v1/registrations/admin/team/registrations/export/ — streams an .xlsx, one row per team."""

    permission_classes = [IsAuthenticated, IsStaffRole]

    COLUMNS = [
        ("Reference", lambda r: r.registration_number),
        ("Status", lambda r: r.status),
        ("Team name", lambda r: r.team_name),
        ("Company/Institution", lambda r: r.company_or_institution),
        ("Relay category", lambda r: r.relay_category),
        ("Captain name", lambda r: f"{r.captain_first_name} {r.captain_last_name}".strip()),
        ("Captain email", lambda r: r.captain_email),
        ("Captain phone", lambda r: r.captain_phone),
        ("Category", lambda r: r.category.name),
        ("Roster size", lambda r: r.roster.count()),
        ("Roster", lambda r: ", ".join(runner.full_name for runner in r.roster.all())),
        ("Amount", lambda r: float(r.amount)),
        ("Currency", lambda r: r.currency),
        ("Registered at", lambda r: r.registered_at.replace(tzinfo=None) if r.registered_at else None),
    ]

    def get(self, request):
        teams = TeamRegistration.objects.select_related("category").prefetch_related("roster").order_by(
            "-registered_at"
        )

        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Team registrations"

        for col_index, (header, _) in enumerate(self.COLUMNS, start=1):
            sheet.cell(row=1, column=col_index, value=header)

        for row_index, team in enumerate(teams, start=2):
            for col_index, (_, getter) in enumerate(self.COLUMNS, start=1):
                sheet.cell(row=row_index, column=col_index, value=getter(team))

        for col_index in range(1, len(self.COLUMNS) + 1):
            sheet.column_dimensions[get_column_letter(col_index)].width = 24

        buffer = io.BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="kopala-icr-team-registrations.xlsx"'
        return response
