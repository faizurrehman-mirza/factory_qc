from django.test import TestCase
from django.core.exceptions import ValidationError

from inspections.models import ChecklistTemplate
from masters.models import Part
from travelers.models import JobTraveler, ProcessOperation
from travelers.services import complete_operation, start_operation


class OperationSequenceTests(TestCase):
    def setUp(self):
        part = Part.objects.create(part_number="ROUTE-001", name="Routing Test Part")
        template = ChecklistTemplate.objects.create(
            part=part,
            name="Routing Test Checklist",
            revision="A",
            status=ChecklistTemplate.Status.ACTIVE,
        )
        self.traveler = JobTraveler.objects.create(
            traveler_number="JT-ROUTE-001",
            part=part,
            checklist_template=template,
        )
        self.op10 = ProcessOperation.objects.create(
            traveler=self.traveler,
            sequence=10,
            name="Cutting",
        )
        self.op20 = ProcessOperation.objects.create(
            traveler=self.traveler,
            sequence=20,
            name="Turning",
        )
        self.op30 = ProcessOperation.objects.create(
            traveler=self.traveler,
            sequence=30,
            name="Grinding",
        )

    def test_cannot_start_later_operation_before_earlier_one_is_completed(self):
        with self.assertRaises(ValidationError):
            start_operation(self.op30)

        self.assertEqual(self.op30.status, ProcessOperation.Status.PENDING)

    def test_operations_can_start_and_complete_in_sequence(self):
        start_operation(self.op10)
        self.op10.refresh_from_db()
        self.assertEqual(self.op10.status, ProcessOperation.Status.IN_PROGRESS)
        self.assertIsNotNone(self.op10.actual_start)

        with self.assertRaises(ValidationError):
            start_operation(self.op20)

        complete_operation(self.op10)
        self.op10.refresh_from_db()
        self.assertEqual(self.op10.status, ProcessOperation.Status.COMPLETED)
        self.assertIsNotNone(self.op10.actual_end)

        start_operation(self.op20)
        complete_operation(self.op20)
        start_operation(self.op30)

        self.op30.refresh_from_db()
        self.assertEqual(self.op30.status, ProcessOperation.Status.IN_PROGRESS)

    def test_cannot_complete_operation_that_has_not_started(self):
        with self.assertRaises(ValidationError):
            complete_operation(self.op10)

        self.op10.refresh_from_db()
        self.assertEqual(self.op10.status, ProcessOperation.Status.PENDING)
        self.assertIsNone(self.op10.actual_end)

    def test_completing_last_operation_completes_traveler(self):
        start_operation(self.op10)
        complete_operation(self.op10)
        start_operation(self.op20)
        complete_operation(self.op20)
        start_operation(self.op30)
        complete_operation(self.op30)

        self.traveler.refresh_from_db()
        self.assertEqual(self.traveler.status, JobTraveler.Status.COMPLETED)

    def test_starting_first_operation_moves_traveler_to_in_progress(self):
        start_operation(self.op10)

        self.traveler.refresh_from_db()
        self.assertEqual(self.traveler.status, JobTraveler.Status.IN_PROGRESS)

    def test_on_hold_traveler_cannot_start_operation(self):
        self.traveler.status = JobTraveler.Status.ON_HOLD
        self.traveler.save(update_fields=["status"])

        with self.assertRaises(ValidationError):
            start_operation(self.op10)

        self.op10.refresh_from_db()
        self.assertEqual(self.op10.status, ProcessOperation.Status.PENDING)
