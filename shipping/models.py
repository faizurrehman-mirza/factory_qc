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

    def save(self, *args, **kwargs):
        if self.status == self.Status.RELEASED:
            allowed, reason = self.can_be_released()
            if not allowed:
                from django.core.exceptions import ValidationError
                raise ValidationError(f"Cannot release Gate Pass: {reason}")

            if not self.released_at:
                from django.utils import timezone
                self.released_at = timezone.now()

        super().save(*args, **kwargs)

    
    def can_be_released(self):
        """
        Improved shipping interlock.
        """
        traveler = self.traveler

        # 1. All operations must be COMPLETED (not just not PENDING)
        if not traveler.operations.exists():
            return False, "At least one process operation is required before shipping."

        incomplete_ops = traveler.operations.exclude(status="COMPLETED")
        if incomplete_ops.exists():
            return False, "All process operations must be completed before shipping."

        # 2. The latest inspection must be APPROVED or CONCESSION.
        latest_inspection = traveler.inspection_sessions.order_by(
            "-started_at", "-pk"
        ).first()
        if latest_inspection is None or latest_inspection.status not in (
            "APPROVED",
            "CONCESSION",
        ):
            return False, "The latest inspection must be approved or have a concession."

        return True, "All quality checks passed."