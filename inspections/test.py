from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from masters.models import Factory, Part, Machine, Gauge
from inspections.models import (
    ChecklistTemplate, TemplateField,
    InspectionSession, Measurement, ApprovalRecord
)
from travelers.models import JobTraveler, ProcessOperation
from inspections.services import validate_gauge, submit_inspection, decide_approval


class BusinessRulesTests(TestCase):

    def setUp(self):
        # Create basic data
        self.factory = Factory.objects.create(name="Test Factory", code="TF-01")
        self.part = Part.objects.create(part_number="TEST-001", name="Test Part")
        self.machine = Machine.objects.create(
            factory=self.factory,
            name="Test CNC",
            code="CNC-T1",
            last_pm_date=timezone.now().date()
        )

        self.template = ChecklistTemplate.objects.create(
            part=self.part,
            name="Test PDI",
            revision="A",
            status="ACTIVE"
        )

        self.field = TemplateField.objects.create(
            template=self.template,
            sequence=1,
            label="Diameter",
            field_type="DIMENSION",
            nominal_value=25.000,
            upper_tolerance=0.050,
            lower_tolerance=0.020,
            is_ctq=True,
            is_required=True
        )

        self.inspector = User.objects.create_user(
            username="inspector1",
            email="inspector1@test.com",
            password="test123",
            role=User.Role.FLOOR_INSPECTOR
        )

        self.supervisor = User.objects.create_user(
            username="supervisor1",
            email="supervisor1@test.com",
            password="test123",
            role=User.Role.SHIFT_SUPERVISOR
        )
                

        self.traveler = JobTraveler.objects.create(
            traveler_number="JT-TEST-001",
            part=self.part,
            quantity=10,
            checklist_template=self.template
        )

        self.valid_gauge = Gauge.objects.create(
            name="Good Vernier",
            serial_number="VC-GOOD",
            calibration_expiry_date=timezone.now().date() + timedelta(days=30)
        )

        self.expired_gauge = Gauge.objects.create(
            name="Expired Vernier",
            serial_number="VC-EXPIRED",
            calibration_expiry_date=timezone.now().date() - timedelta(days=10)
        )
    def test_supervisor_can_approve(self):
        """Supervisor should be able to approve a submitted inspection"""
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
            status="SUBMITTED"
        )

        Measurement.objects.create(
            session=session,
            template_field=self.field,
            measured_value=25.010,
            gauge=self.valid_gauge
        )

        approval = decide_approval(
            session=session,
            user=self.supervisor,
            decision="APPROVED",
            comments="Looks good"
        )

        self.assertEqual(approval.decision, "APPROVED")
        session.refresh_from_db()
        self.assertEqual(session.status, "APPROVED")

    def test_inspector_cannot_approve(self):
        """Floor Inspector should not be allowed to approve"""
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
            status="SUBMITTED"
        )

        with self.assertRaises(ValidationError):
            decide_approval(
                session=session,
                user=self.inspector,
                decision="APPROVED"
            )


    def test_expired_gauge_is_blocked(self):
        """Expired gauge should raise ValidationError"""
        with self.assertRaises(ValidationError):
            validate_gauge(self.expired_gauge)

    def test_valid_gauge_passes(self):
        """Valid gauge should not raise error"""
        try:
            validate_gauge(self.valid_gauge)
        except ValidationError:
            self.fail("Valid gauge should not raise ValidationError")

    def test_fail_without_photo_cannot_submit(self):
        """Cannot submit inspection if a FAIL has no photo"""
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
            machine=self.machine
        )

        Measurement.objects.create(
            session=session,
            template_field=self.field,
            measured_value=26.000,  # This will be FAIL
            gauge=self.valid_gauge
        )

        with self.assertRaises(ValidationError):
            submit_inspection(session, self.inspector)

    def test_ctq_fail_cannot_get_concession(self):
        """CTQ failure should not allow concession"""
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
            status="SUBMITTED"
        )

        Measurement.objects.create(
            session=session,
            template_field=self.field,
            measured_value=26.000,  # FAIL + CTQ
            gauge=self.valid_gauge,
            result="FAIL"
        )

        with self.assertRaises(ValidationError):
            decide_approval(
                session=session,
                user=self.supervisor,
                decision="CONCESSION",
                concession_reason="Looks okay"
            )