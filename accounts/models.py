from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        """
        Using TextChoices is the modern, clean way in Django.
        It gives us readable names + database values + validation.
        """

        PLANT_MANAGER = "PLANT_MANAGER", "Plant / General Manager"
        QUALITY_ENGINEER = "QUALITY_ENGINEER", "Quality Engineer"
        QUALITY_MANAGER = "QUALITY_MANAGER", "Quality Manager"
        SHIFT_SUPERVISOR = "SHIFT_SUPERVISOR", "Shift Supervisor"
        FLOOR_INSPECTOR = "FLOOR_INSPECTOR", "QA Floor Inspector"
        OPERATOR = "OPERATOR", "Machine Operator"

        # we keep username as the login field
        # email will be unique for better identification

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.FLOOR_INSPECTOR,
        help_text="determines what the user can see and do in the system",
    )

    employee_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        help_text="Company employee ID / badge number"
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["username"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    # ---------- Helper methods (keep logic inside the model) ----------
    def is_plant_manager(self):
        return self.role == self.Role.PLANT_MANAGER

    def is_quality_engineer(self):
        return self.role == self.Role.QUALITY_ENGINEER

    def is_quality_manager(self):
        return self.role == self.Role.QUALITY_MANAGER

    def is_shift_supervisor(self):
        return self.role == self.Role.SHIFT_SUPERVISOR

    def is_floor_inspector(self):
        return self.role == self.Role.FLOOR_INSPECTOR

    def is_operator(self):
        return self.role == self.Role.OPERATOR
