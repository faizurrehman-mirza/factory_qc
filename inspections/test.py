from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from accounts.models import User
from masters.models import Factory, Part, Machine, Gauge
from inspections.models import (
    ChecklistTemplate, TemplateField,
    InspectionSession, Measurement, DefectPhoto, ApprovalRecord
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

    def test_existing_measurement_can_be_saved_after_gauge_expires(self):
        """Later gauge expiry must not invalidate an existing measurement."""
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
        )
        measurement = Measurement.objects.create(
            session=session,
            template_field=self.field,
            measured_value=25.010,
            gauge=self.valid_gauge,
        )

        self.valid_gauge.calibration_expiry_date = timezone.now().date() - timedelta(days=1)
        self.valid_gauge.save(update_fields=["calibration_expiry_date"])
        measurement.remarks = "Historical record updated"
        measurement.save()

        measurement.refresh_from_db()
        self.assertEqual(measurement.remarks, "Historical record updated")

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

    def test_failed_measurement_with_one_photo_cannot_submit(self):
        """A failed measurement needs at least two defect photos."""
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
        )
        measurement = Measurement.objects.create(
            session=session,
            template_field=self.field,
            measured_value=26.000,
            gauge=self.valid_gauge,
        )
        DefectPhoto.objects.create(
            measurement=measurement,
            image="defect_photos/defect-1.jpg",
        )

        with self.assertRaises(ValidationError):
            submit_inspection(session, self.inspector)

    def test_failed_measurement_with_two_photos_can_submit(self):
        """A failed measurement with two defect photos can be submitted."""
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
        )
        measurement = Measurement.objects.create(
            session=session,
            template_field=self.field,
            measured_value=26.000,
            gauge=self.valid_gauge,
        )
        for photo_name in ("defect-1.jpg", "defect-2.jpg"):
            DefectPhoto.objects.create(
                measurement=measurement,
                image=f"defect_photos/{photo_name}",
            )

        submitted_session = submit_inspection(session, self.inspector)

        self.assertEqual(submitted_session.status, InspectionSession.Status.SUBMITTED)

    def test_another_inspector_cannot_submit_session(self):
        """Only the inspector assigned to a session can submit it."""
        other_inspector = User.objects.create_user(
            username="inspector2",
            email="inspector2@test.com",
            role=User.Role.FLOOR_INSPECTOR,
        )
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
        )
        Measurement.objects.create(
            session=session,
            template_field=self.field,
            measured_value=25.010,
            gauge=self.valid_gauge,
        )

        with self.assertRaises(ValidationError):
            submit_inspection(session, other_inspector)

        session.refresh_from_db()
        self.assertEqual(session.status, InspectionSession.Status.IN_PROGRESS)
        self.assertIsNone(session.submitted_at)

    def test_missing_required_field_cannot_submit(self):
        """Cannot submit if a required template field has no measurement"""
        TemplateField.objects.create(
            template=self.template,
            sequence=2,
            label="Roughness",
            field_type="MAX_THRESHOLD",
            threshold_value=0.8,
            is_required=True,
        )
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
        )
        # Only the Diameter field is measured, Roughness is skipped
        Measurement.objects.create(
            session=session,
            template_field=self.field,
            measured_value=25.010,
            gauge=self.valid_gauge,
        )

        with self.assertRaises(ValidationError) as ctx:
            submit_inspection(session, self.inspector)

        self.assertIn("Roughness", str(ctx.exception))

    def test_dimension_without_gauge_is_blocked(self):
        """A measured value must name the gauge used"""
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
        )
        with self.assertRaises(ValidationError):
            Measurement.objects.create(
                session=session,
                template_field=self.field,   # DIMENSION field
                measured_value=25.010,
                # no gauge
            )

    def test_visual_check_does_not_need_a_gauge(self):
        """Visual pass/fail checks use no instrument"""
        visual = TemplateField.objects.create(
            template=self.template,
            sequence=2,
            label="Free of burrs",
            field_type="VISUAL",
            is_required=True,
        )
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
        )
        m = Measurement.objects.create(
            session=session,
            template_field=visual,
            visual_result="PASS",
        )
        self.assertEqual(m.result, "PASS")

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

    def test_failed_measurement_cannot_be_approved(self):
        """A failed measurement must not receive ordinary approval."""
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
            status=InspectionSession.Status.SUBMITTED,
        )
        Measurement.objects.create(
            session=session,
            template_field=self.field,
            measured_value=26.000,
            gauge=self.valid_gauge,
        )

        with self.assertRaises(ValidationError):
            decide_approval(
                session=session,
                user=self.supervisor,
                decision=ApprovalRecord.Decision.APPROVED,
            )

        self.assertFalse(ApprovalRecord.objects.filter(session=session).exists())
        session.refresh_from_db()
        self.assertEqual(session.status, InspectionSession.Status.SUBMITTED)

    def test_invalid_approval_decision_is_rejected_without_record(self):
        """Unsupported decisions must not create incomplete approval records."""
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
            status=InspectionSession.Status.SUBMITTED,
        )

        with self.assertRaises(ValidationError):
            decide_approval(
                session=session,
                user=self.supervisor,
                decision="INVALID",
            )

        self.assertFalse(ApprovalRecord.objects.filter(session=session).exists())
        session.refresh_from_db()
        self.assertEqual(session.status, InspectionSession.Status.SUBMITTED)