from django.urls import path

from .views import (
    PublicExtraRunnerFeeView,
    PublicIndividualCategoryListView,
    PublicIndividualRegistrationCreateView,
    PublicRegistrationLookupView,
    PublicTeamCategoryListView,
    PublicTeamRegistrationCreateView,
    TeamMeView,
    TeamRosterAddView,
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
    path(
        "registrations/team/extra-runner-fee/",
        PublicExtraRunnerFeeView.as_view(),
        name="team-extra-runner-fee",
    ),
    path("registrations/team/", PublicTeamRegistrationCreateView.as_view(), name="team-registration-create"),
    # Lookup
    path("registrations/lookup/", PublicRegistrationLookupView.as_view(), name="registration-lookup"),
    # Logged-in team account
    path("team/me/", TeamMeView.as_view(), name="team-me"),
    path("team/me/roster/", TeamRosterAddView.as_view(), name="team-roster-add"),
]
