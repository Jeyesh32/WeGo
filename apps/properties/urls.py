from django.urls import path

from apps.properties.views import PropertyDetailView, PropertyListCreateView, RoomDetailView, RoomListCreateView, sample_agoda_api_view

urlpatterns = [
    path("", PropertyListCreateView.as_view(), name="property-list-create"),
    path("<uuid:pk>/", PropertyDetailView.as_view(), name="property-detail"),
    path("<uuid:pk>/sample-agoda/", sample_agoda_api_view, name="property-sample-agoda"),
    path("rooms/", RoomListCreateView.as_view(), name="room-list-create"),
    path("rooms/<uuid:pk>/", RoomDetailView.as_view(), name="room-detail"),
]
