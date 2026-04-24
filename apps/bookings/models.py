from django.db import models
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db.models import F, Q
from django.db.models.functions import Lower
from django.db.backends.postgresql.psycopg_any import DateTimeTZRange

from apps.common.models import TimestampedModel, UUIDPrimaryKeyModel


class BookingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    AWAITING_PAYMENT = "awaiting_payment", "Awaiting Payment"
    CONFIRMED = "confirmed", "Confirmed"
    CHECKED_IN = "checked_in", "Checked In"
    CHECKED_OUT = "checked_out", "Checked Out"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"
    EXPIRED = "expired", "Expired"


class Booking(TimestampedModel):
    booking_number = models.CharField(max_length=40, unique=True)
    customer_user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.RESTRICT, related_name="bookings")
    property = models.ForeignKey("properties.Property", on_delete=models.RESTRICT, related_name="bookings")
    room = models.ForeignKey("properties.Room", on_delete=models.RESTRICT, related_name="bookings")
    rate_plan = models.ForeignKey("properties.RoomRatePlan", on_delete=models.SET_NULL, null=True, blank=True)
    hourly_rate = models.ForeignKey("properties.RoomHourlyRate", on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey("vendors.VendorStaff", on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    source_channel = models.CharField(max_length=30, default="web")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    booking_window = DateTimeRangeField(null=True, blank=True)
    adult_count = models.IntegerField(default=1)
    child_count = models.IntegerField(default=0)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency_code = models.CharField(max_length=3, default="USD")
    special_requests = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "bookings"
        constraints = [
            ExclusionConstraint(
                name="no_overlapping_active_bookings",
                expressions=[
                    ("room", RangeOperators.EQUAL),
                    ("booking_window", RangeOperators.OVERLAPS),
                ],
                condition=Q(status__in=[BookingStatus.CONFIRMED, BookingStatus.CHECKED_IN]),
            )
        ]
        indexes = [
            models.Index(fields=["customer_user"]),
            models.Index(fields=["vendor"]),
            models.Index(fields=["property"]),
            models.Index(fields=["room"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        if self.starts_at and self.ends_at:
            self.booking_window = DateTimeTZRange(self.starts_at, self.ends_at, "[)")
        super().save(*args, **kwargs)


class BookingGuest(UUIDPrimaryKeyModel):
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE, related_name="guests")
    full_name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "booking_guests"


class BookingStatusHistory(UUIDPrimaryKeyModel):
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE, related_name="status_history")
    old_status = models.CharField(max_length=20, choices=BookingStatus.choices, blank=True)
    new_status = models.CharField(max_length=20, choices=BookingStatus.choices)
    changed_by_user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "booking_status_history"


class Coupon(TimestampedModel):
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.CASCADE, null=True, blank=True, related_name="coupons")
    code = models.CharField(max_length=40)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    max_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    minimum_order_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    usage_limit = models.IntegerField(null=True, blank=True)
    per_user_limit = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "coupons"
        constraints = [
            models.UniqueConstraint(
                Lower("code"),
                condition=Q(vendor__isnull=True),
                name="uq_coupons_platform_code",
            ),
            models.UniqueConstraint(
                Lower("code"),
                F("vendor"),
                condition=Q(vendor__isnull=False),
                name="uq_coupons_vendor_code",
            ),
        ]


class BookingCoupon(models.Model):
    booking = models.ForeignKey("bookings.Booking", on_delete=models.CASCADE)
    coupon = models.ForeignKey("bookings.Coupon", on_delete=models.RESTRICT)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "booking_coupons"
        unique_together = [("booking", "coupon")]


class Review(TimestampedModel):
    booking = models.OneToOneField("bookings.Booking", on_delete=models.SET_NULL, null=True, blank=True)
    reviewer_user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.CASCADE, null=True, blank=True)
    property = models.ForeignKey("properties.Property", on_delete=models.CASCADE, null=True, blank=True)
    room = models.ForeignKey("properties.Room", on_delete=models.CASCADE, null=True, blank=True)
    rating = models.SmallIntegerField()
    title = models.CharField(max_length=160, blank=True)
    body = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "reviews"


class Favorite(models.Model):
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    room = models.ForeignKey("properties.Room", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "favorites"
        unique_together = [("user", "room")]


class ContactInquiry(UUIDPrimaryKeyModel):
    property = models.ForeignKey("properties.Property", on_delete=models.SET_NULL, null=True, blank=True)
    room = models.ForeignKey("properties.Room", on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.SET_NULL, null=True, blank=True)
    sender_user = models.ForeignKey("users.User", on_delete=models.SET_NULL, null=True, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, default="new")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contact_inquiries"
