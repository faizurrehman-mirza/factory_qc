from django.contrib import admin
from .models import JobTraveler, ProcessOperation


class ProcessOperationInline(admin.TabularInline):
    model = ProcessOperation
    extra = 1
    ordering = ("sequence",)
    fields = (
        "sequence",
        "name",
        "machine",
        "status",
        "remarks",
    )


@admin.register(JobTraveler)
class JobTravelerAdmin(admin.ModelAdmin):
    list_display = (
        "traveler_number",
        "part",
        "quantity",
        "status",
        "checklist_template",
        "created_at",
    )
    list_filter = ("status", "part")
    search_fields = ("traveler_number", "part__part_number")
    inlines = [ProcessOperationInline]
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": (
                "traveler_number",
                "part",
                "quantity",
                "status",
                "checklist_template",
            )
        }),
        ("Additional Info", {
            "fields": ("created_by", "notes")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(ProcessOperation)
class ProcessOperationAdmin(admin.ModelAdmin):
    list_display = ("traveler", "sequence", "name", "machine", "status")
    list_filter = ("status",)
    search_fields = ("name", "traveler__traveler_number")
    ordering = ("traveler", "sequence")