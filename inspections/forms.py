from django import forms
from django.core.exceptions import ValidationError

from masters.models import Gauge
from travelers.models import JobTraveler

from .models import InspectionSession, Measurement, TemplateField


class InspectionStartForm(forms.Form):
    traveler = forms.ModelChoiceField(
        queryset=JobTraveler.objects.none(),
        label="Job traveler",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["traveler"].queryset = JobTraveler.objects.filter(
            checklist_template__status="ACTIVE",
            status__in=[JobTraveler.Status.CREATED, JobTraveler.Status.IN_PROGRESS],
        ).select_related("part", "checklist_template")


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data and not initial:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super().clean(file, initial) for file in files]


class InspectionEntryForm(forms.Form):
    def __init__(self, *args, session: InspectionSession, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.template_fields = list(session.template.fields.all())
        self.existing_measurements = {
            measurement.template_field_id: measurement
            for measurement in session.measurements.prefetch_related("photos")
        }

        for template_field in self.template_fields:
            measurement = self.existing_measurements.get(template_field.pk)
            field_id = template_field.pk
            if template_field.field_type == TemplateField.FieldType.VISUAL:
                self.fields[f"visual_{field_id}"] = forms.ChoiceField(
                    label=template_field.label,
                    choices=[("", "Select result"), *Measurement.Result.choices[:2]],
                    required=template_field.is_required,
                    initial=measurement.visual_result if measurement else None,
                    help_text=template_field.help_text,
                )
            else:
                self.fields[f"value_{field_id}"] = forms.DecimalField(
                    label=template_field.label,
                    required=template_field.is_required,
                    max_digits=10,
                    decimal_places=3,
                    initial=measurement.measured_value if measurement else None,
                    help_text=self._field_help(template_field),
                )
                self.fields[f"gauge_{field_id}"] = forms.ModelChoiceField(
                    label=f"{template_field.label} gauge",
                    queryset=Gauge.objects.filter(is_active=True).order_by("serial_number"),
                    required=False,
                    initial=measurement.gauge if measurement else None,
                )

            self.fields[f"photos_{field_id}"] = MultipleFileField(
                label=f"{template_field.label} defect photos",
                required=False,
            )

    @staticmethod
    def _field_help(template_field):
        if template_field.field_type == TemplateField.FieldType.DIMENSION:
            nominal = template_field.nominal_value
            if nominal is None:
                return template_field.help_text
            lower = template_field.lower_tolerance or 0
            upper = template_field.upper_tolerance or 0
            return (
                f"Allowed: {nominal - lower} to {nominal + upper} "
                f"{template_field.unit}."
            )
        return template_field.help_text

    def clean(self):
        cleaned_data = super().clean()
        for template_field in self.template_fields:
            field_id = template_field.pk
            value = (
                cleaned_data.get(f"visual_{field_id}")
                if template_field.field_type == TemplateField.FieldType.VISUAL
                else cleaned_data.get(f"value_{field_id}")
            )
            if template_field.field_type != TemplateField.FieldType.VISUAL and value is not None:
                if not cleaned_data.get(f"gauge_{field_id}"):
                    self.add_error(
                        f"gauge_{field_id}",
                        "Select the gauge used for this measurement.",
                    )

            existing = self.existing_measurements.get(field_id)
            photo_count = len(cleaned_data.get(f"photos_{field_id}", []))
            if existing:
                photo_count += existing.photos.count()

            measurement = Measurement(
                session=self.session,
                template_field=template_field,
                measured_value=(
                    value
                    if template_field.field_type != TemplateField.FieldType.VISUAL
                    else None
                ),
                visual_result=(
                    value
                    if template_field.field_type == TemplateField.FieldType.VISUAL
                    else None
                ),
            )
            result = measurement.calculate_result()
            if result == Measurement.Result.FAIL and photo_count < 2:
                self.add_error(
                    f"photos_{field_id}",
                    ValidationError("At least two defect photos are required for a failure."),
                )
        return cleaned_data
