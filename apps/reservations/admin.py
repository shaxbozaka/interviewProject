from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ["user", "book", "status", "reserved_at", "due_date"]
    list_filter = ["status"]
