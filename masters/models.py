from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Machine(models.Model):
    """
    Represents a physical machine or workstation on the shopfloor.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        UNDER_MAINTENANCE = "UNDER_MAINTENANCE", "Under Maintenance"
        INACTIVE = "INACTIVE", "Inactive"

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique name of the machine "
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short code used for QR codes"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )

    # Daily Preventive Maintenance tracking
    last_pm_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when the last Preventive Maintenance was done"
    )

    pm_due_days = models.PositiveIntegerField(
        default=1,
        help_text="How many days after last PM the machine becomes overdue"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Machine"
        verbose_name_plural = "Machines"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def is_pm_overdue(self):
        """
        Returns True if Preventive Maintenance is overdue.
        This will later be used to lock the machine on the tablet.
        """
        if not self.last_pm_date:
            return True  # Never done PM → consider overdue

        days_passed = (timezone.now().date() - self.last_pm_date).days
        return days_passed >= self.pm_due_days


class Gauge(models.Model):
    """
    Measuring instruments used by inspectors.
    """

    class GaugeType(models.TextChoices):
        VERNIER = "VERNIER", "Vernier Caliper"
        MICROMETER = "MICROMETER", "Micrometer"
        HEIGHT_GAUGE = "HEIGHT_GAUGE", "Height Gauge"
        PLUG_GAUGE = "PLUG_GAUGE", "Plug Gauge"
        THREAD_GAUGE = "THREAD_GAUGE", "Thread Gauge"
        CMM = "CMM", "CMM Machine"
        OTHER = "OTHER", "Other"

    name = models.CharField(max_length=100)
    serial_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique serial number of the gauge"
    )

    gauge_type = models.CharField(
        max_length=20,
        choices=GaugeType.choices,
        default=GaugeType.VERNIER
    )

    calibration_expiry_date = models.DateField(
        help_text="Date after which this gauge cannot be used"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Gauge"
        verbose_name_plural = "Gauges"
        ordering = ["serial_number"]

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    def is_calibration_expired(self):
        """
        Returns True if the gauge calibration has expired.
        This will be used to block measurement entry on tablets.
        """
        return self.calibration_expiry_date < timezone.now().date()

    def clean(self):
        """
        Extra validation that runs when saving from forms/admin.
        """
        if self.calibration_expiry_date and self.calibration_expiry_date < timezone.now().date():
            # We allow saving expired gauges (for history), but we can warn
            pass