from django.db import models
from masters.models import Part


class ChecklistTemplate(models.Model):
    """
    A reusable inspection checklist linked to a specific Part.
    Example: Final PDI - Shaft 25mm - Rev B
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        ARCHIVED = "ARCHIVED", "Archived"

    part = models.ForeignKey(
        Part,
        on_delete=models.PROTECT,
        related_name="checklist_templates",
        help_text="Which part this checklist belongs to"
    )

    name = models.CharField(
        max_length=150,
        help_text="Name of the checklist (e.g. Final PDI - Shaft 25mm)"
    )

    revision = models.CharField(
        max_length=10,
        default="A",
        help_text="Revision (A, B, C...)"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    version_notes = models.TextField(
        blank=True,
        help_text="What changed in this revision"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Checklist Template"
        verbose_name_plural = "Checklist Templates"
        ordering = ["-created_at"]
        unique_together = [["part", "name", "revision"]]

    def __str__(self):
        return f"{self.name} (Rev {self.revision})"


class TemplateField(models.Model):
    """
    Individual inspection point inside a Checklist Template.
    """

    class FieldType(models.TextChoices):
        DIMENSION = "DIMENSION", "Dimension (± tolerance)"
        MAX_THRESHOLD = "MAX_THRESHOLD", "Maximum Threshold"
        MIN_THRESHOLD = "MIN_THRESHOLD", "Minimum Threshold"
        VISUAL = "VISUAL", "Visual Pass/Fail"

    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.CASCADE,
        related_name="fields"
    )

    sequence = models.PositiveIntegerField(
        default=1,
        help_text="Display order on the tablet"
    )

    label = models.CharField(
        max_length=150,
        help_text="What the inspector sees (e.g. Shaft Diameter)"
    )

    field_type = models.CharField(
        max_length=20,
        choices=FieldType.choices,
        default=FieldType.DIMENSION
    )

    # Used when field_type = DIMENSION
    nominal_value = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Target value (e.g. 25.000)"
    )
    upper_tolerance = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Plus tolerance (e.g. +0.050)"
    )
    lower_tolerance = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Minus tolerance (e.g. -0.020)"
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        default="mm"
    )

    # Used when field_type = MAX_THRESHOLD or MIN_THRESHOLD
    threshold_value = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True
    )

    is_ctq = models.BooleanField(
        default=False,
        help_text="Critical-to-Quality characteristic"
    )

    is_required = models.BooleanField(
        default=True
    )

    help_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Extra instruction shown to the inspector"
    )

    class Meta:
        verbose_name = "Template Field"
        verbose_name_plural = "Template Fields"
        ordering = ["sequence"]

    def __str__(self):
        return f"{self.sequence}. {self.label}"