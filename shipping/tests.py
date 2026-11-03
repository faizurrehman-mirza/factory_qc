from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from inspections.models import ChecklistTemplate, InspectionSession
from masters.models import Part
from shipping.models import GatePass
from travelers.models import JobTraveler, ProcessOperation


class GatePassReleaseTests(TestCase):
    def setUp(self):
        self.part = Part.objects.create(part_number="SHIP-001", name="Shipping Test Part")
        self.template = ChecklistTemplate.objects.create(
            part=self.part,
            name="Final Inspection",
            revision="A",
            status=ChecklistTemplate.Status.ACTIVE,
        )
        self.traveler = JobTraveler.objects.create(
            traveler_number="JT-SHIP-001",
            part=self.part,
            checklist_template=self.template,
        )

    def add_completed_operation(self):
        return ProcessOperation.objects.create(
            traveler=self.traveler,
            sequence=10,
            name="Final operation",
            status=ProcessOperation.Status.COMPLETED,
        )

    def add_inspection(self, status):
        return InspectionSession.objects.create(
            traveler=self.traveler,
            template=self.template,
            status=status,
        )

    def create_gate_pass(self):
        return GatePass(
            gate_pass_number="GP-SHIP-001",
            traveler=self.traveler,
            status=GatePass.Status.RELEASED,
        )

    def test_release_requires_at_least_one_operation(self):
        self.add_inspection(InspectionSession.Status.APPROVED)

        allowed, reason = self.create_gate_pass().can_be_released()

        self.assertFalse(allowed)
        self.assertIn("at least one", reason.lower())

    def test_latest_inspection_must_be_approved_or_concession(self):
        self.add_completed_operation()
        self.add_inspection(InspectionSession.Status.APPROVED)
        self.add_inspection(InspectionSession.Status.REJECTED)

        allowed, reason = self.create_gate_pass().can_be_released()

        self.assertFalse(allowed)
        self.assertIn("latest", reason.lower())

    def test_release_allowed_when_operations_and_latest_inspection_are_cleared(self):
        self.add_completed_operation()
        self.add_inspection(InspectionSession.Status.APPROVED)

        allowed, reason = self.create_gate_pass().can_be_released()

        self.assertTrue(allowed)
        self.assertEqual(reason, "All quality checks passed.")

    def test_gate_pass_screen_releases_only_after_interlocks_pass(self):
        supervisor = User.objects.create_user(
            username="shipping-supervisor",
            email="shipping-supervisor@example.com",
            role=User.Role.SHIFT_SUPERVISOR,
        )
        self.add_completed_operation()
        self.add_inspection(InspectionSession.Status.APPROVED)
        self.client.force_login(supervisor)

        response = self.client.post(
            reverse("gate-pass-list"),
            {
                "gate_pass_number": "GP-WEB-001",
                "traveler": self.traveler.pk,
                "vehicle_number": "TEST-123",
            },
        )

        self.assertRedirects(response, reverse("gate-pass-list"))
        gate_pass = GatePass.objects.get(gate_pass_number="GP-WEB-001")
        self.assertEqual(gate_pass.status, GatePass.Status.RELEASED)
        self.assertEqual(gate_pass.created_by, supervisor)

    def test_gate_pass_screen_shows_interlock_failure(self):
        supervisor = User.objects.create_user(
            username="blocked-shipping-supervisor",
            email="blocked-shipping@example.com",
            role=User.Role.SHIFT_SUPERVISOR,
        )
        self.add_inspection(InspectionSession.Status.APPROVED)
        self.client.force_login(supervisor)

        response = self.client.post(
            reverse("gate-pass-list"),
            {
                "gate_pass_number": "GP-BLOCKED-001",
                "traveler": self.traveler.pk,
                "vehicle_number": "TEST-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(GatePass.objects.filter(traveler=self.traveler).exists())
        self.assertContains(response, "At least one process operation is required")
