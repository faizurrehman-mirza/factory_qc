from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import JobTraveler, ProcessOperation
from .services import complete_operation, start_operation


class ProcessOperationInline(admin.TabularInline):
    model = ProcessOperation
    extra = 1
    ordering = ("sequence",)
    readonly_fields = ("status",)
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
    readonly_fields = ("status", "actual_start", "actual_end")
    actions = ("start_selected_operation", "complete_selected_operation")

    @admin.action(description="Start selected operation (select exactly one)")
    def start_selected_operation(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                "Select exactly one operation to start.",
                level=messages.ERROR,
            )
            return

        try:
            start_operation(queryset.get())
        except ValidationError as error:
            self.message_user(request, error, level=messages.ERROR)
            return

        self.message_user(request, "Operation started.")

    @admin.action(description="Complete selected operation (select exactly one)")
    def complete_selected_operation(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                "Select exactly one operation to complete.",
                level=messages.ERROR,
            )
            return

        try:
            complete_operation(queryset.get())
        except ValidationError as error:
            self.message_user(request, error, level=messages.ERROR)
            return

        self.message_user(request, "Operation completed.")