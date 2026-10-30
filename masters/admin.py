from django.contrib import admin
from .models import Machine, Gauge


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "status", "last_pm_date", "is_pm_overdue_display")
    list_filter = ("status",)
    search_fields = ("name", "code")
    readonly_fields = ("created_at", "updated_at")

    def is_pm_overdue_display(self, obj):
        return obj.is_pm_overdue()

    is_pm_overdue_display.boolean = True
    is_pm_overdue_display.short_description = "PM Overdue?"


@admin.register(Gauge)
class GaugeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "serial_number",
        "gauge_type",
        "calibration_expiry_date",
        "is_expired_display",
        "is_active",
    )
    list_filter = ("gauge_type", "is_active")
    search_fields = ("name", "serial_number")
    readonly_fields = ("created_at", "updated_at")

    def is_expired_display(self, obj):
        return obj.is_calibration_expired()

    is_expired_display.boolean = True
    is_expired_display.short_description = "Calibration Expired?"
