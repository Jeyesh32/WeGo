from rest_framework import generics, permissions

from apps.properties.models import Property, Room
from apps.properties.serializers import PropertySerializer, RoomSerializer


class PropertyListCreateView(generics.ListCreateAPIView):
    serializer_class = PropertySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Property.objects.select_related("vendor").prefetch_related(
            "rooms__rate_plans__hourly_rates"
        ).order_by("-created_at")
        city = self.request.query_params.get("city")
        status_value = self.request.query_params.get("status")
        if city:
            queryset = queryset.filter(city__iexact=city)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class PropertyDetailView(generics.RetrieveAPIView):
    queryset = Property.objects.select_related("vendor").prefetch_related("rooms__rate_plans__hourly_rates")
    serializer_class = PropertySerializer
    permission_classes = [permissions.AllowAny]


class RoomListCreateView(generics.ListCreateAPIView):
    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Room.objects.select_related("property").prefetch_related("rate_plans__hourly_rates").order_by("-created_at")
        property_id = self.request.query_params.get("property_id")
        status_value = self.request.query_params.get("status")
        if property_id:
            queryset = queryset.filter(property_id=property_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class RoomDetailView(generics.RetrieveAPIView):
    queryset = Room.objects.select_related("property").prefetch_related("rate_plans__hourly_rates")
    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]
