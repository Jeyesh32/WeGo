from rest_framework import generics, permissions

from apps.payments.models import Payment
from apps.payments.serializers import PaymentSerializer


class PaymentListCreateView(generics.ListCreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Payment.objects.select_related("booking", "payer_user").prefetch_related("refunds").order_by("-created_at")
        booking_id = self.request.query_params.get("booking_id")
        status_value = self.request.query_params.get("status")
        if booking_id:
            queryset = queryset.filter(booking_id=booking_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset


class PaymentDetailView(generics.RetrieveUpdateAPIView):
    queryset = Payment.objects.select_related("booking", "payer_user").prefetch_related("refunds")
    serializer_class = PaymentSerializer
    permission_classes = [permissions.AllowAny]
