from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import User

from .forms import InspectionEntryForm, InspectionStartForm
from .models import (
    DefectPhoto,
    InspectionSession,
    Measurement,
    TemplateField,
)
from .services import decide_approval, submit_inspection


def _require_inspector(user):
    if user.role != User.Role.FLOOR_INSPECTOR:
        raise PermissionDenied


def _require_approver(user):
    if user.role not in (
        User.Role.SHIFT_SUPERVISOR,
        User.Role.QUALITY_MANAGER,
        User.Role.PLANT_MANAGER,
    ):
        raise PermissionDenied


@login_required
def inspection_list(request):
    _require_inspector(request.user)
    form = InspectionStartForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        traveler = form.cleaned_data["traveler"]
        session = InspectionSession.objects.create(
            traveler=traveler,
            template=traveler.checklist_template,
            inspector=request.user,
        )
        return redirect("inspection-detail", session_id=session.pk)

    sessions = InspectionSession.objects.filter(
        inspector=request.user,
        status=InspectionSession.Status.IN_PROGRESS,
    ).select_related("traveler", "template")
    return render(
        request,
        "inspections/inspection_list.html",
        {"form": form, "sessions": sessions},
    )


@login_required
def inspection_detail(request, session_id):
    _require_inspector(request.user)
    session = get_object_or_404(
        InspectionSession.objects.select_related("traveler", "template"),
        pk=session_id,
        inspector=request.user,
        status=InspectionSession.Status.IN_PROGRESS,
    )
    form = InspectionEntryForm(
        request.POST or None,
        request.FILES or None,
        session=session,
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                for template_field in form.template_fields:
                    field_id = template_field.pk
                    is_visual = (
                        template_field.field_type == TemplateField.FieldType.VISUAL
                    )
                    value = form.cleaned_data.get(
                        f"visual_{field_id}" if is_visual else f"value_{field_id}"
                    )
                    gauge = (
                        None
                        if is_visual
                        else form.cleaned_data.get(f"gauge_{field_id}")
                    )
                    photos = form.cleaned_data.get(f"photos_{field_id}", [])
                    measurement = form.existing_measurements.get(field_id)

                    if value in (None, "") and measurement is None and not photos:
                        continue

                    if measurement is None:
                        measurement = Measurement(
                            session=session,
                            template_field=template_field,
                        )
                    if is_visual:
                        measurement.visual_result = value or None
                    else:
                        measurement.measured_value = value
                        measurement.gauge = gauge
                    measurement.save()

                    for photo in photos:
                        DefectPhoto.objects.create(
                            measurement=measurement,
                            image=photo,
                        )

                submit_inspection(session, request.user)
        except ValidationError as error:
            messages.error(request, error)
        else:
            messages.success(request, "Inspection submitted for supervisor review.")
            return redirect("inspection-list")

    return render(
        request,
        "inspections/inspection_detail.html",
        {"form": form, "session": session},
    )


@login_required
def approval_queue(request):
    _require_approver(request.user)
    sessions = InspectionSession.objects.filter(
        status=InspectionSession.Status.SUBMITTED
    ).select_related("traveler", "template", "inspector")
    return render(
        request,
        "inspections/approval_queue.html",
        {"sessions": sessions},
    )


@login_required
def approval_detail(request, session_id):
    _require_approver(request.user)
    session = get_object_or_404(
        InspectionSession.objects.select_related("traveler", "template", "inspector"),
        pk=session_id,
        status=InspectionSession.Status.SUBMITTED,
    )
    if request.method == "POST":
        decision = request.POST.get("decision", "")
        try:
            decide_approval(
                session=session,
                user=request.user,
                decision=decision,
                comments=request.POST.get("comments", ""),
                concession_reason=request.POST.get("concession_reason", ""),
            )
        except ValidationError as error:
            messages.error(request, error)
        else:
            messages.success(request, "Inspection decision recorded.")
            return redirect("approval-queue")

    measurements = session.measurements.select_related(
        "template_field", "gauge"
    ).prefetch_related("photos")
    return render(
        request,
        "inspections/approval_detail.html",
        {"session": session, "measurements": measurements},
    )
