from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import User


def workbench(request):
    if not request.user.is_authenticated:
        return redirect("login")

    if request.user.role == User.Role.FLOOR_INSPECTOR:
        return redirect("inspection-list")

    if request.user.role in (
        User.Role.SHIFT_SUPERVISOR,
        User.Role.QUALITY_MANAGER,
        User.Role.PLANT_MANAGER,
    ):
        return redirect("approval-queue")

    if request.user.is_staff:
        return redirect("admin:index")

    raise PermissionDenied
