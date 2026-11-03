from django.test import TestCase

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
