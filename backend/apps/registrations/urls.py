from django.urls import path

from .views import (
    AdminIndividualBulkUploadTemplateView,
    AdminIndividualBulkUploadView,
    AdminIndividualDashboardView,
    AdminIndividualExportView,
    AdminIndividualFilterOptionsView,
    AdminIndividualRegistrationCreateView,
    AdminIndividualRegistrationDetailView,
    AdminIndividualRegistrationListView,
    AdminTeamDashboardView,
    AdminTeamExportView,
    AdminTeamFilterOptionsView,
    AdminTeamRegistrationCreateView,
    AdminTeamRegistrationDetailView,
    AdminTeamRegistrationListView,
    PublicIndividualCategoryListView,
    PublicIndividualRegistrationCreateView,
    PublicRegistrationLookupView,
    PublicTeamCategoryListView,
    PublicTeamRegistrationCreateView,
    PublicVendorCategoryListView,
    PublicVendorRegistrationCreateView,
)

urlpatterns = [
    # Individual — public
    path(
        "registrations/individual/categories/",
        PublicIndividualCategoryListView.as_view(),
        name="individual-category-list",
    ),
    path(
        "registrations/individual/",
        PublicIndividualRegistrationCreateView.as_view(),
        name="individual-registration-create",
    ),
    # Team — public
    path("registrations/team/categories/", PublicTeamCategoryListView.as_view(), name="team-category-list"),
    path("registrations/team/", PublicTeamRegistrationCreateView.as_view(), name="team-registration-create"),
    # Vendor — public
    path("registrations/vendor/categories/", PublicVendorCategoryListView.as_view(), name="vendor-category-list"),
    path("registrations/vendor/", PublicVendorRegistrationCreateView.as_view(), name="vendor-registration-create"),
    # Lookup — public
    path("registrations/lookup/", PublicRegistrationLookupView.as_view(), name="registration-lookup"),
    # Individual — admin
    path(
        "registrations/admin/individual/dashboard/",
        AdminIndividualDashboardView.as_view(),
        name="admin-individual-dashboard",
    ),
    path(
        "registrations/admin/individual/filters/",
        AdminIndividualFilterOptionsView.as_view(),
        name="admin-individual-filters",
    ),
    path(
        "registrations/admin/individual/registrations/",
        AdminIndividualRegistrationListView.as_view(),
        name="admin-individual-registration-list",
    ),
    path(
        "registrations/admin/individual/registrations/create/",
        AdminIndividualRegistrationCreateView.as_view(),
        name="admin-individual-registration-create",
    ),
    path(
        "registrations/admin/individual/registrations/export/",
        AdminIndividualExportView.as_view(),
        name="admin-individual-registration-export",
    ),
    path(
        "registrations/admin/individual/registrations/bulk-upload/template/",
        AdminIndividualBulkUploadTemplateView.as_view(),
        name="admin-individual-bulk-upload-template",
    ),
    path(
        "registrations/admin/individual/registrations/bulk-upload/",
        AdminIndividualBulkUploadView.as_view(),
        name="admin-individual-bulk-upload",
    ),
    path(
        "registrations/admin/individual/registrations/<uuid:pk>/",
        AdminIndividualRegistrationDetailView.as_view(),
        name="admin-individual-registration-detail",
    ),
    # Team — admin
    path("registrations/admin/team/dashboard/", AdminTeamDashboardView.as_view(), name="admin-team-dashboard"),
    path("registrations/admin/team/filters/", AdminTeamFilterOptionsView.as_view(), name="admin-team-filters"),
    path(
        "registrations/admin/team/registrations/",
        AdminTeamRegistrationListView.as_view(),
        name="admin-team-registration-list",
    ),
    path(
        "registrations/admin/team/registrations/create/",
        AdminTeamRegistrationCreateView.as_view(),
        name="admin-team-registration-create",
    ),
    path(
        "registrations/admin/team/registrations/export/",
        AdminTeamExportView.as_view(),
        name="admin-team-registration-export",
    ),
    path(
        "registrations/admin/team/registrations/<uuid:pk>/",
        AdminTeamRegistrationDetailView.as_view(),
        name="admin-team-registration-detail",
    ),
]
