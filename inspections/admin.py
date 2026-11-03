from django.contrib import admin
from .models import ChecklistTemplate, TemplateField
from .models import InspectionSession, Measurement, DefectPhoto



class TemplateFieldInline(admin.TabularInline):
    """
    Allows adding multiple fields directly inside the Checklist Template page.
    """
    model = TemplateField
    extra = 1
    ordering = ("sequence",)
    fields = (
        "sequence",
        "label",
        "field_type",
        "nominal_value",
        "upper_tolerance",
        "lower_tolerance",
        "unit",
        "threshold_value",
        "is_ctq",
        "is_required",
        "help_text",
    )


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "part", "revision", "status", "created_at")
    list_filter = ("status", "part")
    search_fields = ("name", "part__part_number", "part__name")
    inlines = [TemplateFieldInline]
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("part", "name", "revision", "status")
        }),
        ("Notes", {
            "fields": ("version_notes",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(TemplateField)
class TemplateFieldAdmin(admin.ModelAdmin):
    list_display = ("template", "sequence", "label", "field_type", "is_ctq", "is_required")
    list_filter = ("field_type", "is_ctq", "template__part")
    search_fields = ("label", "template__name")
    ordering = ("template", "sequence")




class MeasurementInline(admin.TabularInline):
    model = Measurement
    extra = 0
    readonly_fields = ("measured_at",)
    fields = (
        "template_field",
        "measured_value",
        "visual_result",
        "result",
        "gauge",
        "remarks",
    )


class DefectPhotoInline(admin.TabularInline):
    model = DefectPhoto
    extra = 0
    readonly_fields = ("uploaded_at",)


@admin.register(InspectionSession)
class InspectionSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "traveler",
        "template",
        "inspector",
        "machine",
        "status",
        "started_at",
        "submitted_at",
    )
    list_filter = ("status", "machine")
    search_fields = ("traveler__traveler_number", "inspector__username")
    inlines = [MeasurementInline]
    readonly_fields = ("started_at", "submitted_at")


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = (
        "session",
        "template_field",
        "measured_value",
        "result",
        "gauge",
        "measured_at",
    )
    list_filter = ("result",)
    search_fields = ("template_field__label", "session__traveler__traveler_number")
    inlines = [DefectPhotoInline]


@admin.register(DefectPhoto)
class DefectPhotoAdmin(admin.ModelAdmin):
    list_display = ("measurement", "caption", "uploaded_at")
    readonly_fields = ("uploaded_at",)