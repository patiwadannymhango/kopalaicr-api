from django.urls import path

from .views import (
    PublicIndividualCategoryListView,
    PublicIndividualRegistrationCreateView,
    PublicRegistrationLookupView,
    PublicTeamCategoryListView,
    PublicTeamRegistrationCreateView,
)

urlpatterns = [
    # Individual
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
    # Team
    path("registrations/team/categories/", PublicTeamCategoryListView.as_view(), name="team-category-list"),
    path("registrations/team/", PublicTeamRegistrationCreateView.as_view(), name="team-registration-create"),
    # Lookup
    path("registrations/lookup/", PublicRegistrationLookupView.as_view(), name="registration-lookup"),
]
