from django.contrib import admin
from .models import ChecklistTemplate, TemplateField


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