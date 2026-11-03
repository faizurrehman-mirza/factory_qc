from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from masters.models import Gauge
from .models import InspectionSession, Measurement, ApprovalRecord


def validate_gauge(gauge: Gauge):
    """
    Rule: Expired gauges cannot be used for measurement.
    """
    if gauge is None:
        raise ValidationError("A gauge must be selected for this measurement.")

    if not gauge.is_active:
        raise ValidationError(f"Gauge {gauge.serial_number} is inactive.")

    if gauge.is_calibration_expired():
        raise ValidationError(
            f"Gauge {gauge.serial_number} calibration has expired on {gauge.calibration_expiry_date}."
        )


def submit_inspection(session: InspectionSession, user):
    """
    Rule: An inspection can only be submitted if:
    - The submitting user is the assigned inspector
    - All required fields are filled
    - Every FAIL measurement has at least two photos
    """
    if session.status != InspectionSession.Status.IN_PROGRESS:
        raise ValidationError("Only inspections in progress can be submitted.")

    if session.inspector_id != user.pk:
        raise ValidationError("Only the assigned inspector can submit this inspection.")

    measurements = session.measurements.all()

    if not measurements.exists():
        raise ValidationError("Cannot submit an empty inspection.")

    for m in measurements:
        field = m.template_field

        # Required field check
        if field.is_required:
            if field.field_type == field.FieldType.VISUAL:
                if not m.visual_result:
                    raise ValidationError(f"'{field.label}' is required.")
            else:
                if m.measured_value is None:
                    raise ValidationError(f"'{field.label}' is required.")

        # Photo required on FAIL
        if m.result == Measurement.Result.FAIL:
            if m.photos.count() < 2:
                raise ValidationError(
                    f"Measurement '{field.label}' has failed. At least two defect photos are required."
                )

    required_ids = set(
        session.template.fields.filter(is_required=True).values_list("id", flat=True)
    )
    measured_ids = set(measurements.values_list("template_field_id", flat=True))
    missing_ids = required_ids - measured_ids

    if missing_ids:
        labels = session.template.fields.filter(id__in=missing_ids).values_list("label", flat=True)
        raise ValidationError(f"Missing required fields: {', '.join(labels)}")

    # All good → submit
    session.status = InspectionSession.Status.SUBMITTED
    session.submitted_at = timezone.now()
    session.save(update_fields=["status", "submitted_at"])

    return session


@transaction.atomic
def decide_approval(session: InspectionSession, user, decision: str, comments: str = "", concession_reason: str = ""):
    """
    Rules:
    - Only Supervisor / Quality Manager / Plant Manager can approve
    - Failed measurements cannot receive ordinary approval
    - CTQ failure cannot get a Concession
    - Concession requires a reason
    """
    allowed_roles = [
        user.Role.SHIFT_SUPERVISOR,
        user.Role.QUALITY_MANAGER,
        user.Role.PLANT_MANAGER,
    ]

    if user.role not in allowed_roles:
        raise ValidationError("You do not have permission to approve inspections.")

    if decision not in ApprovalRecord.Decision.values:
        raise ValidationError("Invalid inspection decision.")

    if session.status != InspectionSession.Status.SUBMITTED:
        raise ValidationError("Only submitted inspections can be decided.")

    if decision == ApprovalRecord.Decision.APPROVED:
        has_failed_measurement = session.measurements.filter(
            result=Measurement.Result.FAIL
        ).exists()
        if has_failed_measurement:
            raise ValidationError("Cannot approve an inspection with failed measurements.")

    # CTQ protection
    if decision == ApprovalRecord.Decision.CONCESSION:
        has_ctq_fail = session.measurements.filter(
            result=Measurement.Result.FAIL,
            template_field__is_ctq=True
        ).exists()

        if has_ctq_fail:
            raise ValidationError("Cannot give concession on a Critical-to-Quality (CTQ) failure.")

        if not concession_reason.strip():
            raise ValidationError("Concession reason is required.")

    # Create approval record
    approval = ApprovalRecord.objects.create(
        session=session,
        decision=decision,
        decided_by=user,
        comments=comments,
        concession_reason=concession_reason if decision == ApprovalRecord.Decision.CONCESSION else ""
    )

    # Update session status
    if decision == ApprovalRecord.Decision.APPROVED:
        session.status = InspectionSession.Status.APPROVED
    elif decision == ApprovalRecord.Decision.REJECTED:
        session.status = InspectionSession.Status.REJECTED
    elif decision == ApprovalRecord.Decision.CONCESSION:
        session.status = InspectionSession.Status.CONCESSION

    session.save(update_fields=["status"])

    return approval