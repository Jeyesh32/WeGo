from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import DeviceToken, Notification, User, UserAddress


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "role", "status", "is_staff", "is_active", "created_at")
    list_filter = ("role", "status", "is_staff", "is_active")
    search_fields = ("email", "display_name", "first_name", "last_name", "phone")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("first_name", "last_name", "display_name", "phone", "avatar_url")}),
        ("Status", {"fields": ("role", "status", "email_verified_at", "phone_verified_at", "deleted_at")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Activity", {"fields": ("last_login", "last_login_at", "metadata")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "role", "status", "is_staff", "is_active"),
            },
        ),
    )


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "city", "state", "country_code", "is_default")
    search_fields = ("user__email", "line_1", "city", "state", "postal_code")
    list_filter = ("country_code", "is_default")


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "app_version", "last_seen_at", "created_at")
    search_fields = ("user__email", "device_token")
    list_filter = ("platform",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "title", "read_at", "created_at")
    search_fields = ("user__email", "title", "body")
    list_filter = ("notification_type",)
