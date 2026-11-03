from django.db import models
from django.conf import settings
from masters.models import Part, Machine
from inspections.models import ChecklistTemplate


class JobTraveler(models.Model):
    """
    Digital Job Traveler for a production lot.
    """

    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        ON_HOLD = "ON_HOLD", "On Hold"
        CANCELLED = "CANCELLED", "Cancelled"

    traveler_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique traveler / job number"
    )

    part = models.ForeignKey(
        Part,
        on_delete=models.PROTECT,
        related_name="travelers"
    )

    quantity = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED
    )

    checklist_template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="travelers",
        help_text="Which inspection checklist to use"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_travelers"
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Job Traveler"
        verbose_name_plural = "Job Travelers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.traveler_number} - {self.part.part_number}"


class ProcessOperation(models.Model):
    """
    One step in the manufacturing process of a Job Traveler.
    Example: Op 10 - Rough Turning, Op 20 - Heat Treatment, etc.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        SKIPPED = "SKIPPED", "Skipped"

    traveler = models.ForeignKey(
        JobTraveler,
        on_delete=models.CASCADE,
        related_name="operations"
    )

    sequence = models.PositiveIntegerField(
        help_text="Order of this operation (10, 20, 30...)"
    )

    name = models.CharField(
        max_length=150,
        help_text="Name of the operation (e.g. CNC Rough Turning)"
    )

    machine = models.ForeignKey(
        Machine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operations"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    planned_start = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)

    remarks = models.TextField(blank=True)

    class Meta:
        verbose_name = "Process Operation"
        verbose_name_plural = "Process Operations"
        ordering = ["sequence"]
        unique_together = [["traveler", "sequence"]]

    def __str__(self):
        return f"Op {self.sequence} - {self.name}"