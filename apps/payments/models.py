from django.db import models

from apps.common.models import TimestampedModel, UUIDPrimaryKeyModel


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    AUTHORIZED = "authorized", "Authorized"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"
    PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"
    VOIDED = "voided", "Voided"


class PaymentProvider(models.TextChoices):
    CASH = "cash", "Cash"
    STRIPE = "stripe", "Stripe"
    RAZORPAY = "razorpay", "Razorpay"
    PAYPAL = "paypal", "Paypal"
    PAYSTACK = "paystack", "Paystack"
    FLUTTERWAVE = "flutterwave", "Flutterwave"
    MANUAL = "manual", "Manual"
    OTHER = "other", "Other"


class Payment(TimestampedModel):
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE, related_name="payments")
    payer_user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.CharField(max_length=20, choices=PaymentProvider.choices)
    provider_reference = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency_code = models.CharField(max_length=3, default="USD")
    paid_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "payments"
        indexes = [models.Index(fields=["booking"]), models.Index(fields=["provider_reference"])]


class Refund(UUIDPrimaryKeyModel):
    payment = models.ForeignKey("payments.Payment", on_delete=models.CASCADE, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True)
    provider_reference = models.CharField(max_length=160, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "refunds"
