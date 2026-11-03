from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render

from accounts.models import User

from .forms import GatePassReleaseForm, create_gate_pass
from .models import GatePass


@login_required
def gate_pass_list(request):
    if request.user.role not in (
        User.Role.SHIFT_SUPERVISOR,
        User.Role.QUALITY_MANAGER,
        User.Role.PLANT_MANAGER,
    ):
        raise PermissionDenied

    form = GatePassReleaseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            create_gate_pass(form, request.user)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Gate pass released.")
            return redirect("gate-pass-list")

    gate_passes = GatePass.objects.select_related("traveler").all()
    return render(
        request,
        "shipping/gate_pass_list.html",
        {"form": form, "gate_passes": gate_passes},
    )
