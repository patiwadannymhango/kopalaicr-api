from django.urls import path

from .views import TeamCaptainLoginView

urlpatterns = [
    path("team/login/", TeamCaptainLoginView.as_view(), name="team-captain-login"),
]
