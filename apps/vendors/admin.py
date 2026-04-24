from django.contrib import admin

from apps.vendors.models import SubscriptionPlan, Vendor, VendorStaff, VendorSubscription


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("brand_name", "owner_user", "status", "currency_code", "rating_avg", "created_at")
    search_fields = ("brand_name", "legal_name", "slug", "owner_user__email")
    list_filter = ("status", "currency_code")
    prepopulated_fields = {"slug": ("brand_name",)}


@admin.register(VendorStaff)
class VendorStaffAdmin(admin.ModelAdmin):
    list_display = ("vendor", "user", "staff_role", "is_active", "created_at")
    search_fields = ("vendor__brand_name", "user__email", "staff_role")
    list_filter = ("staff_role", "is_active")


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "billing_interval", "price", "currency_code", "is_active")
    search_fields = ("name", "slug")
    list_filter = ("billing_interval", "is_active")


@admin.register(VendorSubscription)
class VendorSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("vendor", "plan", "status", "starts_at", "ends_at", "auto_renew")
    search_fields = ("vendor__brand_name", "plan__name", "external_reference")
    list_filter = ("status", "auto_renew")
