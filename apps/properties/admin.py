from django.contrib import admin

from apps.properties.models import (
    MediaAsset,
    Property,
    PropertyAmenity,
    PropertyAmenityMap,
    PropertyBlackout,
    Room,
    RoomAmenity,
    RoomAmenityMap,
    RoomBlackout,
    RoomDailyRate,
    RoomHourlyRate,
    RoomRatePlan,
)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("property_name", "vendor", "city", "country_code", "status", "featured")
    search_fields = ("property_name", "slug", "city", "vendor__brand_name")
    list_filter = ("status", "featured", "country_code", "city")
    prepopulated_fields = {"slug": ("property_name",)}


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("room_name", "property", "status", "quantity", "featured")
    search_fields = ("room_name", "slug", "property__property_name")
    list_filter = ("status", "featured")
    prepopulated_fields = {"slug": ("room_name",)}


admin.site.register(PropertyAmenity)
admin.site.register(PropertyAmenityMap)
admin.site.register(PropertyBlackout)
admin.site.register(RoomAmenity)
admin.site.register(RoomAmenityMap)
admin.site.register(RoomBlackout)
admin.site.register(RoomRatePlan)
admin.site.register(RoomHourlyRate)
admin.site.register(RoomDailyRate)
admin.site.register(MediaAsset)
