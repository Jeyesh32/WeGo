from django.contrib import admin

from apps.payments.models import Payment, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("booking", "provider", "status", "amount", "currency_code", "paid_at")
    search_fields = ("booking__booking_number", "provider_reference")
    list_filter = ("provider", "status", "currency_code")


admin.site.register(Refund)
