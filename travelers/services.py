from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import JobTraveler, ProcessOperation


@transaction.atomic
def start_operation(operation: ProcessOperation) -> ProcessOperation:
    operation = ProcessOperation.objects.select_for_update().get(pk=operation.pk)
    traveler = JobTraveler.objects.select_for_update().get(pk=operation.traveler_id)

    if traveler.status in (
        JobTraveler.Status.ON_HOLD,
        JobTraveler.Status.CANCELLED,
        JobTraveler.Status.COMPLETED,
    ):
        raise ValidationError(
            f"Cannot start an operation while traveler is {traveler.get_status_display().lower()}."
        )

    if operation.status != ProcessOperation.Status.PENDING:
        raise ValidationError("Only pending operations can be started.")

    earlier_incomplete = traveler.operations.filter(
        sequence__lt=operation.sequence
    ).exclude(status=ProcessOperation.Status.COMPLETED)
    if earlier_incomplete.exists():
        raise ValidationError("All earlier operations must be completed first.")

    operation.status = ProcessOperation.Status.IN_PROGRESS
    operation.actual_start = timezone.now()
    operation.save(update_fields=["status", "actual_start"])

    if traveler.status == JobTraveler.Status.CREATED:
        traveler.status = JobTraveler.Status.IN_PROGRESS
        traveler.save(update_fields=["status", "updated_at"])

    return operation


@transaction.atomic
def complete_operation(operation: ProcessOperation) -> ProcessOperation:
    operation = ProcessOperation.objects.select_for_update().get(pk=operation.pk)
    traveler = JobTraveler.objects.select_for_update().get(pk=operation.traveler_id)

    if operation.status != ProcessOperation.Status.IN_PROGRESS:
        raise ValidationError("Only in-progress operations can be completed.")

    operation.status = ProcessOperation.Status.COMPLETED
    operation.actual_end = timezone.now()
    operation.save(update_fields=["status", "actual_end"])

    if not traveler.operations.exclude(
        status=ProcessOperation.Status.COMPLETED
    ).exists():
        traveler.status = JobTraveler.Status.COMPLETED
        traveler.save(update_fields=["status", "updated_at"])

    return operation
