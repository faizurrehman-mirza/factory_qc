from django import forms

from travelers.models import JobTraveler

from .models import GatePass


class GatePassReleaseForm(forms.ModelForm):
    class Meta:
        model = GatePass
        fields = ("gate_pass_number", "traveler", "vehicle_number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["traveler"].queryset = JobTraveler.objects.exclude(
            gate_pass__isnull=False
        ).select_related("part")


def create_gate_pass(form, user):
    gate_pass = form.save(commit=False)
    gate_pass.status = GatePass.Status.RELEASED
    gate_pass.created_by = user
    gate_pass.save()
    return gate_pass
