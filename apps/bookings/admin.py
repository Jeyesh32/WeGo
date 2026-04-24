from django.contrib import admin

from apps.bookings.models import (
    Booking,
    BookingCoupon,
    BookingGuest,
    BookingStatusHistory,
    ContactInquiry,
    Coupon,
    Favorite,
    Review,
)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("booking_number", "customer_user", "property", "room", "status", "starts_at", "ends_at")
    search_fields = ("booking_number", "customer_user__email", "property__property_name", "room__room_name")
    list_filter = ("status", "source_channel", "currency_code")


admin.site.register(BookingGuest)
admin.site.register(BookingStatusHistory)
admin.site.register(Coupon)
admin.site.register(BookingCoupon)
admin.site.register(Review)
admin.site.register(Favorite)
admin.site.register(ContactInquiry)
