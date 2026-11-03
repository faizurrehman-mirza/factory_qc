from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from masters.models import Gauge, Part
from travelers.models import JobTraveler

from .models import (
    ApprovalRecord,
    ChecklistTemplate,
    InspectionSession,
    Measurement,
    TemplateField,
)


class InspectionWorkbenchTests(TestCase):
    def setUp(self):
        self.part = Part.objects.create(part_number="WEB-001", name="Workbench Part")
        self.template = ChecklistTemplate.objects.create(
            part=self.part,
            name="Workbench Checklist",
            revision="A",
            status=ChecklistTemplate.Status.ACTIVE,
        )
        self.field = TemplateField.objects.create(
            template=self.template,
            sequence=1,
            label="Diameter",
            field_type=TemplateField.FieldType.DIMENSION,
            nominal_value=25,
            upper_tolerance=0.05,
            lower_tolerance=0.02,
            is_required=True,
        )
        self.traveler = JobTraveler.objects.create(
            traveler_number="JT-WEB-001",
            part=self.part,
            checklist_template=self.template,
        )
        self.gauge = Gauge.objects.create(
            name="Workbench Gauge",
            serial_number="WEB-GAUGE-001",
            calibration_expiry_date=timezone.now().date() + timedelta(days=30),
        )
        self.inspector = User.objects.create_user(
            username="web-inspector",
            email="web-inspector@example.com",
            role=User.Role.FLOOR_INSPECTOR,
        )
        self.supervisor = User.objects.create_user(
            username="web-supervisor",
            email="web-supervisor@example.com",
            role=User.Role.SHIFT_SUPERVISOR,
        )

    def test_inspector_can_start_and_submit_a_passing_checklist(self):
        self.client.force_login(self.inspector)
        response = self.client.post(
            reverse("inspection-list"),
            {"traveler": self.traveler.pk},
        )

        session = InspectionSession.objects.get(traveler=self.traveler)
        self.assertRedirects(
            response,
            reverse("inspection-detail", args=[session.pk]),
        )

        response = self.client.post(
            reverse("inspection-detail", args=[session.pk]),
            {
                f"value_{self.field.pk}": "25.010",
                f"gauge_{self.field.pk}": str(self.gauge.pk),
            },
        )

        self.assertRedirects(response, reverse("inspection-list"))
        session.refresh_from_db()
        self.assertEqual(session.status, InspectionSession.Status.SUBMITTED)
        self.assertEqual(
            session.measurements.get(template_field=self.field).result,
            Measurement.Result.PASS,
        )

    def test_failing_checklist_without_two_photos_is_not_saved(self):
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
        )
        self.client.force_login(self.inspector)

        response = self.client.post(
            reverse("inspection-detail", args=[session.pk]),
            {
                f"value_{self.field.pk}": "26.000",
                f"gauge_{self.field.pk}": str(self.gauge.pk),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(session.measurements.exists())
        session.refresh_from_db()
        self.assertEqual(session.status, InspectionSession.Status.IN_PROGRESS)

    def test_inspector_cannot_open_another_inspectors_session(self):
        other_inspector = User.objects.create_user(
            username="other-inspector",
            email="other-inspector@example.com",
            role=User.Role.FLOOR_INSPECTOR,
        )
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=other_inspector,
        )
        self.client.force_login(self.inspector)

        response = self.client.get(reverse("inspection-detail", args=[session.pk]))

        self.assertEqual(response.status_code, 404)

    def test_supervisor_can_approve_a_submitted_passing_inspection(self):
        session = InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            inspector=self.inspector,
            status=InspectionSession.Status.SUBMITTED,
        )
        Measurement.objects.create(
            session=session,
            template_field=self.field,
            measured_value=Decimal("25.010"),
            gauge=self.gauge,
        )
        self.client.force_login(self.supervisor)

        response = self.client.post(
            reverse("approval-detail", args=[session.pk]),
            {"decision": ApprovalRecord.Decision.APPROVED},
        )

        self.assertRedirects(response, reverse("approval-queue"))
        session.refresh_from_db()
        self.assertEqual(session.status, InspectionSession.Status.APPROVED)
        self.assertEqual(session.approval.decision, ApprovalRecord.Decision.APPROVED)
