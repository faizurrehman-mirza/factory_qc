from django.db import models
from django.utils import timezone


class Factory(models.Model):
    """
    Represents a physical factory / plant / site.
    Example: Main Plant - Pune, Heat Treatment Unit, etc.
    Even if the company currently has only one factory,
    we model it properly for future scalability.
    """

    name = models.CharField(
        max_length=150,
        unique=True,
        help_text="Full name of the factory/plant"
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short unique code (e.g. PUNE-01, HT-UNIT)"
    )

    location = models.CharField(
        max_length=255,
        blank=True,
        help_text="City or full address"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Factory"
        verbose_name_plural = "Factories"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Part(models.Model):
    """
    Represents a manufactured part / component.
    Example: Shaft-25mm, Gear-Type-A, Housing-Casting
    """

    part_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique part number used in the factory"
    )

    name = models.CharField(
        max_length=150,
        help_text="Descriptive name of the part"
    )

    description = models.TextField(
        blank=True,
        help_text="Optional detailed description"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Part"
        verbose_name_plural = "Parts"
        ordering = ["part_number"]

    def __str__(self):
        return f"{self.part_number} - {self.name}"


class Machine(models.Model):
    """
    Represents a physical machine or workstation on the shopfloor.
    Example: CNC Lathe #04, VMC Station #02
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        UNDER_MAINTENANCE = "UNDER_MAINTENANCE", "Under Maintenance"
        INACTIVE = "INACTIVE", "Inactive"

    factory = models.ForeignKey(
        Factory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="machines",
        help_text="Which factory this machine belongs to"
    )

    name = models.CharField(
        max_length=100,
        help_text="Unique name of the machine (e.g. CNC Lathe #04)"
    )

    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short code used for QR codes (e.g. CNC-04)"
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
        # Machine name should be unique within a factory
        unique_together = [["factory", "name"]]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def is_pm_overdue(self):
        """
        Returns True if Preventive Maintenance is overdue.
        Later used to lock the machine on the tablet.
        """
        if not self.last_pm_date:
            return True

        days_passed = (timezone.now().date() - self.last_pm_date).days
        return days_passed >= self.pm_due_days


class Gauge(models.Model):
    """
    Measuring instruments used by inspectors.
    Example: Vernier Caliper #VC-104, Micrometer #MM-12
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
        Used to block measurement entry on tablets.
        """
        return self.calibration_expiry_date < timezone.now().date()