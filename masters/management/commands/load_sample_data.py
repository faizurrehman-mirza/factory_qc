from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from masters.models import Factory, Part, Machine, Gauge
from accounts.models import User
from inspections.models import ChecklistTemplate, TemplateField
from travelers.models import JobTraveler, ProcessOperation


class Command(BaseCommand):
    help = "Load sample data for easy testing of the Factory QC system"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Starting to load sample data...\n"))

        # -------------------------------------------------
        # 1. Create Factories
        # -------------------------------------------------
        factory1, _ = Factory.objects.get_or_create(
            code="PUNE-01",
            defaults={
                "name": "Main Manufacturing Plant - Pune",
                "location": "Pune, Maharashtra",
                "is_active": True,
            }
        )

        factory2, _ = Factory.objects.get_or_create(
            code="HT-01",
            defaults={
                "name": "Heat Treatment Unit",
                "location": "Pune, Maharashtra",
                "is_active": True,
            }
        )
        self.stdout.write("  ✓ Factories created")

        # -------------------------------------------------
        # 2. Create Parts
        # -------------------------------------------------
        Part.objects.get_or_create(
            part_number="SHAFT-25MM",
            defaults={
                "name": "Precision Shaft 25mm",
                "description": "High precision shaft used in gearboxes",
                "is_active": True,
            }
        )

        Part.objects.get_or_create(
            part_number="GEAR-A12",
            defaults={
                "name": "Spur Gear Type A12",
                "description": "Spur gear for transmission assembly",
                "is_active": True,
            }
        )

        Part.objects.get_or_create(
            part_number="HOUSING-CAST",
            defaults={
                "name": "Casting Housing",
                "description": "Main housing casting",
                "is_active": True,
            }
        )
        self.stdout.write("  ✓ Parts created")

        # -------------------------------------------------
        # 3. Create Machines
        # -------------------------------------------------
        Machine.objects.get_or_create(
            code="CNC-04",
            defaults={
                "factory": factory1,
                "name": "CNC Lathe #04",
                "status": Machine.Status.ACTIVE,
                "last_pm_date": timezone.now().date() - timedelta(days=2),
                "pm_due_days": 7,
            }
        )

        Machine.objects.get_or_create(
            code="VMC-02",
            defaults={
                "factory": factory1,
                "name": "VMC Station #02",
                "status": Machine.Status.ACTIVE,
                "last_pm_date": timezone.now().date(),
                "pm_due_days": 1,
            }
        )

        Machine.objects.get_or_create(
            code="HT-OVEN-01",
            defaults={
                "factory": factory2,
                "name": "Heat Treat Oven #01",
                "status": Machine.Status.ACTIVE,
                "last_pm_date": timezone.now().date() - timedelta(days=10),
                "pm_due_days": 7,
            }
        )
        self.stdout.write("  ✓ Machines created")

        # -------------------------------------------------
        # 4. Create Gauges
        # -------------------------------------------------
        Gauge.objects.get_or_create(
            serial_number="VC-104",
            defaults={
                "name": "Vernier Caliper 0-150mm",
                "gauge_type": Gauge.GaugeType.VERNIER,
                "calibration_expiry_date": timezone.now().date() + timedelta(days=180),
                "is_active": True,
            }
        )

        Gauge.objects.get_or_create(
            serial_number="MM-12",
            defaults={
                "name": "Digital Micrometer 0-25mm",
                "gauge_type": Gauge.GaugeType.MICROMETER,
                "calibration_expiry_date": timezone.now().date() + timedelta(days=90),
                "is_active": True,
            }
        )

        Gauge.objects.get_or_create(
            serial_number="VC-099",
            defaults={
                "name": "Old Vernier Caliper (Expired)",
                "gauge_type": Gauge.GaugeType.VERNIER,
                "calibration_expiry_date": timezone.now().date() - timedelta(days=30),
                "is_active": True,
            }
        )
        self.stdout.write("  ✓ Gauges created")

        # -------------------------------------------------
        # 5. Create Users
        # -------------------------------------------------
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@zapuza.com",
                "role": User.Role.PLANT_MANAGER,
                "first_name": "System",
                "last_name": "Admin",
                "employee_id": "EMP000",
                "is_staff": True,
                "is_superuser": True,
            }
        )
        if created:
            admin_user.set_password("Admin@1234")
            admin_user.save()

        other_users = [
            {
                "username": "quality_engineer",
                "email": "qe@zapuza.com",
                "role": User.Role.QUALITY_ENGINEER,
                "first_name": "Priya",
                "last_name": "Patel",
                "employee_id": "EMP002",
            },
            {
                "username": "quality_manager",
                "email": "qm@zapuza.com",
                "role": User.Role.QUALITY_MANAGER,
                "first_name": "Rahul",
                "last_name": "Verma",
                "employee_id": "EMP003",
            },
            {
                "username": "supervisor",
                "email": "ss@zapuza.com",
                "role": User.Role.SHIFT_SUPERVISOR,
                "first_name": "Suresh",
                "last_name": "Kumar",
                "employee_id": "EMP004",
            },
            {
                "username": "inspector",
                "email": "fi@zapuza.com",
                "role": User.Role.FLOOR_INSPECTOR,
                "first_name": "Neha",
                "last_name": "Singh",
                "employee_id": "EMP005",
            },
        ]

        for data in other_users:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data["email"],
                    "role": data["role"],
                    "first_name": data["first_name"],
                    "last_name": data["last_name"],
                    "employee_id": data["employee_id"],
                    "is_staff": False,
                    "is_superuser": False,
                }
            )
            if created:
                user.set_password("Test@1234")
                user.save()

        self.stdout.write("  ✓ Users created")

        # -------------------------------------------------
        # 6. Create Sample Checklist Templates
        # -------------------------------------------------
        try:
            shaft = Part.objects.get(part_number="SHAFT-25MM")
            gear = Part.objects.get(part_number="GEAR-A12")
        except Part.DoesNotExist:
            self.stdout.write(self.style.ERROR("Parts not found."))
            return

        # Template 1 - Shaft
        template1, created = ChecklistTemplate.objects.get_or_create(
            part=shaft,
            name="Final PDI - Shaft 25mm",
            revision="A",
            defaults={
                "status": ChecklistTemplate.Status.ACTIVE,
                "version_notes": "Initial version for assessment"
            }
        )

        if created:
            TemplateField.objects.create(
                template=template1,
                sequence=1,
                label="Shaft Outer Diameter",
                field_type=TemplateField.FieldType.DIMENSION,
                nominal_value=25.000,
                upper_tolerance=0.050,
                lower_tolerance=0.020,
                unit="mm",
                is_ctq=True,
                is_required=True,
                help_text="Measure at mid-point of the shaft"
            )
            TemplateField.objects.create(
                template=template1,
                sequence=2,
                label="Surface Roughness",
                field_type=TemplateField.FieldType.MAX_THRESHOLD,
                threshold_value=0.8,
                unit="Ra",
                is_ctq=False,
                is_required=True
            )
            TemplateField.objects.create(
                template=template1,
                sequence=3,
                label="Visual - Free of Burrs",
                field_type=TemplateField.FieldType.VISUAL,
                is_ctq=False,
                is_required=True,
                help_text="Check edges carefully"
            )

        # Template 2 - Gear
        template2, created = ChecklistTemplate.objects.get_or_create(
            part=gear,
            name="In-Process Check - Gear A12",
            revision="A",
            defaults={
                "status": ChecklistTemplate.Status.ACTIVE,
                "version_notes": "Initial version"
            }
        )

        if created:
            TemplateField.objects.create(
                template=template2,
                sequence=1,
                label="Pitch Diameter",
                field_type=TemplateField.FieldType.DIMENSION,
                nominal_value=48.000,
                upper_tolerance=0.030,
                lower_tolerance=0.030,
                unit="mm",
                is_ctq=True,
                is_required=True
            )
            TemplateField.objects.create(
                template=template2,
                sequence=2,
                label="Visual - Tooth Damage",
                field_type=TemplateField.FieldType.VISUAL,
                is_ctq=True,
                is_required=True
            )

                # -------------------------------------------------
        # 7. Create Sample Job Travelers
        # -------------------------------------------------
        try:
            shaft = Part.objects.get(part_number="SHAFT-25MM")
            gear = Part.objects.get(part_number="GEAR-A12")
            cnc_machine = Machine.objects.get(code="CNC-04")
            vmc_machine = Machine.objects.get(code="VMC-02")
            shaft_template = ChecklistTemplate.objects.filter(part=shaft).first()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading related data: {e}"))
            return

        # Traveler 1 - Shaft
        traveler1, created = JobTraveler.objects.get_or_create(
            traveler_number="JT-2026-001",
            defaults={
                "part": shaft,
                "quantity": 50,
                "status": JobTraveler.Status.IN_PROGRESS,
                "checklist_template": shaft_template,
                "notes": "Sample traveler for assessment"
            }
        )

        if created:
            ProcessOperation.objects.create(
                traveler=traveler1,
                sequence=10,
                name="CNC Rough Turning",
                machine=cnc_machine,
                status=ProcessOperation.Status.COMPLETED
            )
            ProcessOperation.objects.create(
                traveler=traveler1,
                sequence=20,
                name="CNC Finish Turning",
                machine=cnc_machine,
                status=ProcessOperation.Status.IN_PROGRESS
            )
            ProcessOperation.objects.create(
                traveler=traveler1,
                sequence=30,
                name="Final Inspection (PDI)",
                machine=None,
                status=ProcessOperation.Status.PENDING
            )

        # Traveler 2 - Gear
        traveler2, created = JobTraveler.objects.get_or_create(
            traveler_number="JT-2026-002",
            defaults={
                "part": gear,
                "quantity": 30,
                "status": JobTraveler.Status.CREATED,
                "notes": "Second sample traveler"
            }
        )

        if created:
            ProcessOperation.objects.create(
                traveler=traveler2,
                sequence=10,
                name="VMC Roughing",
                machine=vmc_machine,
                status=ProcessOperation.Status.PENDING
            )
            ProcessOperation.objects.create(
                traveler=traveler2,
                sequence=20,
                name="Final Inspection",
                machine=None,
                status=ProcessOperation.Status.PENDING
            )

        self.stdout.write("  ✓ Sample Job Travelers created")

        self.stdout.write("  ✓ Sample Checklist Templates created")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Sample data loaded successfully!"))
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Django Admin Login:"))
        self.stdout.write("  Username : admin")
        self.stdout.write("  Password : Admin@1234")
        self.stdout.write("")
        self.stdout.write("Other users password: Test@1234")