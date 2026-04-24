from django.urls import path

from apps.payments.views import PaymentDetailView, PaymentListCreateView

urlpatterns = [
    path("", PaymentListCreateView.as_view(), name="payment-list-create"),
    path("<uuid:pk>/", PaymentDetailView.as_view(), name="payment-detail"),
]
