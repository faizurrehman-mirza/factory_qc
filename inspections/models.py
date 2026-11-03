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

from django.conf import settings
from travelers.models import JobTraveler, ProcessOperation
from masters.models import Machine, Gauge


class InspectionSession(models.Model):
    """
    One inspection activity performed by a Floor Inspector
    on a specific Job Traveler.
    """

    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CONCESSION = "CONCESSION", "Conditional Concession"

    traveler = models.ForeignKey(
        JobTraveler,
        on_delete=models.PROTECT,
        related_name="inspection_sessions"
    )

    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.PROTECT,
        related_name="sessions"
    )

    machine = models.ForeignKey(
        Machine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspection_sessions"
    )

    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="inspections_done"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS
    )

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Inspection Session"
        verbose_name_plural = "Inspection Sessions"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Inspection of {self.traveler.traveler_number} by {self.inspector}"


class Measurement(models.Model):
    """
    One measurement / check performed during an Inspection Session.
    """

    class Result(models.TextChoices):
        PASS = "PASS", "Pass"
        FAIL = "FAIL", "Fail"
        NA = "NA", "Not Applicable"

    session = models.ForeignKey(
        InspectionSession,
        on_delete=models.CASCADE,
        related_name="measurements"
    )

    template_field = models.ForeignKey(
        TemplateField,
        on_delete=models.PROTECT,
        related_name="measurements"
    )

    # Actual value entered by inspector (for dimension / threshold)
    measured_value = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True
    )

    # For visual checks
    visual_result = models.CharField(
        max_length=10,
        choices=Result.choices,
        null=True,
        blank=True
    )

    result = models.CharField(
        max_length=10,
        choices=Result.choices,
        default=Result.NA
    )

    gauge = models.ForeignKey(
        Gauge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="measurements"
    )

    remarks = models.CharField(max_length=255, blank=True)

    measured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Measurement"
        verbose_name_plural = "Measurements"
        ordering = ["template_field__sequence"]

    def calculate_result(self):
        """
        Automatically decide Pass or Fail based on the template field type
        and the value entered by the inspector.
        """
        field = self.template_field

        # Visual check
        if field.field_type == TemplateField.FieldType.VISUAL:
            if self.visual_result == self.Result.PASS:
                self.result = self.Result.PASS
            elif self.visual_result == self.Result.FAIL:
                self.result = self.Result.FAIL
            else:
                self.result = self.Result.NA
            return self.result

        # Dimension check
        if field.field_type == TemplateField.FieldType.DIMENSION and self.measured_value is not None:
            upper = field.nominal_value + (field.upper_tolerance or 0)
            lower = field.nominal_value - (field.lower_tolerance or 0)

            if lower <= self.measured_value <= upper:
                self.result = self.Result.PASS
            else:
                self.result = self.Result.FAIL
            return self.result

        # Maximum threshold
        if field.field_type == TemplateField.FieldType.MAX_THRESHOLD and self.measured_value is not None:
            if self.measured_value <= field.threshold_value:
                self.result = self.Result.PASS
            else:
                self.result = self.Result.FAIL
            return self.result

        # Minimum threshold
        if field.field_type == TemplateField.FieldType.MIN_THRESHOLD and self.measured_value is not None:
            if self.measured_value >= field.threshold_value:
                self.result = self.Result.PASS
            else:
                self.result = self.Result.FAIL
            return self.result

        self.result = self.Result.NA
        return self.result

    def save(self, *args, **kwargs):
        self.calculate_result()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.template_field.label} - {self.result}"


class DefectPhoto(models.Model):
    """
    Photo taken when a measurement is out of tolerance.
    """

    measurement = models.ForeignKey(
        Measurement,
        on_delete=models.CASCADE,
        related_name="photos"
    )

    image = models.ImageField(upload_to="defect_photos/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Defect Photo"
        verbose_name_plural = "Defect Photos"

    def __str__(self):
        return f"Photo for {self.measurement}"


class ApprovalRecord(models.Model):
    """
    Supervisor decision on an Inspection Session.
    """

    class Decision(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CONCESSION = "CONCESSION", "Conditional Concession"

    session = models.OneToOneField(
        InspectionSession,
        on_delete=models.CASCADE,
        related_name="approval"
    )

    decision = models.CharField(
        max_length=20,
        choices=Decision.choices
    )

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="approvals_made"
    )

    decision_at = models.DateTimeField(auto_now_add=True)

    comments = models.TextField(
        blank=True,
        help_text="Reason for rejection or concession"
    )

    concession_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Required if decision is Concession"
    )

    class Meta:
        verbose_name = "Approval Record"
        verbose_name_plural = "Approval Records"
        ordering = ["-decision_at"]

    def __str__(self):
        return f"{self.session} → {self.decision}"