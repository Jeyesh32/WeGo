from rest_framework import generics, permissions

from apps.bookings.models import Booking
from apps.bookings.serializers import BookingSerializer


class BookingListCreateView(generics.ListCreateAPIView):
    serializer_class = BookingSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Booking.objects.select_related(
            "customer_user", "vendor", "property", "room", "rate_plan", "hourly_rate", "staff"
        ).prefetch_related("guests").order_by("-created_at")
        status_value = self.request.query_params.get("status")
        customer_user_id = self.request.query_params.get("customer_user_id")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if customer_user_id:
            queryset = queryset.filter(customer_user_id=customer_user_id)
        return queryset


class BookingDetailView(generics.RetrieveUpdateAPIView):
    queryset = Booking.objects.select_related(
        "customer_user", "vendor", "property", "room", "rate_plan", "hourly_rate", "staff"
    ).prefetch_related("guests")
    serializer_class = BookingSerializer
    permission_classes = [permissions.AllowAny]
