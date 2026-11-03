from django.db import models
from django.conf import settings
from travelers.models import JobTraveler


class GatePass(models.Model):
    """
    Shipping / Dispatch Gate Pass.
    Can only be created if all quality checks are cleared.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        RELEASED = "RELEASED", "Released"
        CANCELLED = "CANCELLED", "Cancelled"

    gate_pass_number = models.CharField(max_length=50, unique=True)
    traveler = models.OneToOneField(
        JobTraveler,
        on_delete=models.PROTECT,
        related_name="gate_pass"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    released_at = models.DateTimeField(null=True, blank=True)
    vehicle_number = models.CharField(max_length=50, blank=True)
    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Gate Pass"
        verbose_name_plural = "Gate Passes"
        ordering = ["-created_at"]

    def __str__(self):
        return self.gate_pass_number

    def can_be_released(self):
        """
        Basic interlock check.
        Returns (True, "") if allowed, or (False, reason) if blocked.
        """
        traveler = self.traveler

        # 1. Check if there is at least one approved inspection
        approved_sessions = traveler.inspection_sessions.filter(
            status="APPROVED"
        )
        if not approved_sessions.exists():
            return False, "No approved Final Inspection found."

        # 2. Check if any operation is still pending
        pending_ops = traveler.operations.filter(status="PENDING")
        if pending_ops.exists():
            return False, "Some process operations are still pending."

        return True, "All checks passed."