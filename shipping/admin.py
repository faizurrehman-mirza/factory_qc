from django.contrib import admin
from .models import GatePass


@admin.register(GatePass)
class GatePassAdmin(admin.ModelAdmin):
    list_display = ("gate_pass_number", "traveler", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("gate_pass_number", "traveler__traveler_number")
    readonly_fields = ("created_at", "released_at")