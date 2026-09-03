from django.urls import path

from climweb.base.views import participant_map_boundaries

urlpatterns = [
    path(
        "api/participant-map/boundaries",
        participant_map_boundaries,
        name="participant-map-boundaries",
    ),
]
