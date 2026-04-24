from django.db import models

from apps.common.models import TimestampedModel, UUIDPrimaryKeyModel


class VendorStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending Review"
    ACTIVE = "active", "Active"
    REJECTED = "rejected", "Rejected"
    SUSPENDED = "suspended", "Suspended"


class SubscriptionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"


class Vendor(TimestampedModel):
    owner_user = models.ForeignKey("users.User", on_delete=models.RESTRICT, related_name="owned_vendors")
    legal_name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    cover_image_url = models.URLField(blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    timezone = models.CharField(max_length=64, default="UTC")
    currency_code = models.CharField(max_length=3, default="USD")
    status = models.CharField(max_length=20, choices=VendorStatus.choices, default=VendorStatus.PENDING_REVIEW)
    rating_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    rating_count = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "vendors"


class VendorStaff(TimestampedModel):
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.CASCADE, related_name="staff_members")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="vendor_staff_roles")
    staff_role = models.CharField(max_length=40, default="operations")
    title = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    permissions = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vendor_staff"
        unique_together = [("vendor", "user")]


class SubscriptionPlan(TimestampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    billing_interval = models.CharField(max_length=20)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency_code = models.CharField(max_length=3, default="USD")
    trial_days = models.IntegerField(default=0)
    max_properties = models.IntegerField(null=True, blank=True)
    max_rooms = models.IntegerField(null=True, blank=True)
    max_staff = models.IntegerField(null=True, blank=True)
    allows_featured_listing = models.BooleanField(default=False)
    allows_promotions = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    feature_flags = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "subscription_plans"


class VendorSubscription(TimestampedModel):
    vendor = models.ForeignKey("vendors.Vendor", on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey("vendors.SubscriptionPlan", on_delete=models.RESTRICT, related_name="vendor_subscriptions")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=SubscriptionStatus.choices)
    external_reference = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "vendor_subscriptions"
