from django import forms
from businesses.models import Business
from menu.models import MenuCategory, MenuItem, MenuFile


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [super().clean(d, initial) for d in data]

class BusinessForm(forms.ModelForm):
    # Campos de horarios
    mon_start = forms.TimeField(
        required=False,
        label="Lunes (inicio)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )
    mon_end = forms.TimeField(
        required=False,
        label="Lunes (fin)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )

    tue_start = forms.TimeField(
        required=False,
        label="Martes (inicio)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )
    tue_end = forms.TimeField(
        required=False,
        label="Martes (fin)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )

    wed_start = forms.TimeField(
        required=False,
        label="Miércoles (inicio)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )
    wed_end = forms.TimeField(
        required=False,
        label="Miércoles (fin)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )

    thu_start = forms.TimeField(
        required=False,
        label="Jueves (inicio)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )
    thu_end = forms.TimeField(
        required=False,
        label="Jueves (fin)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )

    fri_start = forms.TimeField(
        required=False,
        label="Viernes (inicio)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )
    fri_end = forms.TimeField(
        required=False,
        label="Viernes (fin)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )

    sat_start = forms.TimeField(
        required=False,
        label="Sábado (inicio)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )
    sat_end = forms.TimeField(
        required=False,
        label="Sábado (fin)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )

    sun_start = forms.TimeField(
        required=False,
        label="Domingo (inicio)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )
    sun_end = forms.TimeField(
        required=False,
        label="Domingo (fin)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"})
    )

    avg_prep_time = forms.IntegerField(
        min_value=1,
        max_value=240,
        label="Tiempo promedio de preparación (min)",
        help_text="Ej: 25",
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1", "max": "240"})
    )

    gallery_images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={
            "class": "form-control",
            "accept": "image/*",
        })
    )

    class Meta:
        model = Business
        fields = [
            "name", "business_type", "menu_mode", "service_mode", "zone", "address",
            "latitude", "longitude",
            "phone", "whatsapp", "instagram", "description",
            "tags",
            "logo",
            "cover_image",
            "avg_prep_time",
            "delivery_fee",
            "min_consumption",
            "music_type",
            "night_description",
            "parking_type",
            "parking_cost",
            "nequi_number",
            "is_accepting_orders",
            "allow_table_booking",
            "table_booking_phone",
            "table_booking_message",
        ]

        labels = {
            "is_accepting_orders": "Estoy recibiendo pedidos",
            "tags": "Etiquetas (tags)",
            "delivery_fee": "Costo de domicilio",
            "nequi_number": "Número Nequi",
            "latitude": "Latitud",
            "longitude": "Longitud",
            "service_mode": "Modalidad de entrega",
            "min_consumption": "Consumo mínimo",
            "music_type": "Tipo de música",
        }

        help_texts = {
            "tags": "Separa por coma. Ej: pizza, hamburguesa, café, droguería, mercado",
            "delivery_fee": "Costo fijo del domicilio para este negocio",
            "nequi_number": "Número Nequi donde el cliente debe transferir",
            "latitude": "Latitud del negocio",
            "longitude": "Longitud del negocio",
            "service_mode": "Selecciona si el negocio ofrece domicilio, recogida o ambos",
        }

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "business_type": forms.Select(attrs={"class": "form-select"}),
            "menu_mode": forms.Select(attrs={"class": "form-select"}),
            "service_mode": forms.Select(attrs={"class": "form-select"}),
            "zone": forms.Select(attrs={"class": "form-select"}),
            "address": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "whatsapp": forms.TextInput(attrs={"class": "form-control"}),
            "instagram": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),

            "min_consumption": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: 50000"
            }),
            "music_type": forms.Select(attrs={"class": "form-select"}),

            "tags": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: pizza, hamburguesa, café, droguería, mercado"
            }),
            "delivery_fee": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0"
            }),
            "night_description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe el ambiente del lugar..."
            }),

            "parking_type": forms.Select(attrs={"class": "form-select"}),

            "parking_cost": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: 5000"
            }),

            "nequi_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: 3001234567"
            }),

            "allow_table_booking": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
            "table_booking_phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: 573001112233"
            }),

            "table_booking_message": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Hola, quiero reservar una mesa"
            }),

            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_accepting_orders": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }

    def _format_range(self, start, end) -> str:
        if not start and not end:
            return ""
        if start and not end:
            raise forms.ValidationError("Falta la hora de cierre.")
        if end and not start:
            raise forms.ValidationError("Falta la hora de apertura.")
        if start == end:
            raise forms.ValidationError("La hora de apertura y cierre no pueden ser iguales.")
        return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"

    def _parse_range_str(self, s: str):
        s = (s or "").strip()
        if not s or "-" not in s:
            return None, None
        a, b = s.split("-", 1)
        a = a.strip()
        b = b.strip()
        try:
            sh, sm = [int(x) for x in a.split(":")]
            eh, em = [int(x) for x in b.split(":")]
            from datetime import time as dt_time
            return dt_time(sh, sm), dt_time(eh, em)
        except Exception:
            return None, None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "logo" in self.fields:
            self.fields["logo"].required = False
        if "cover_image" in self.fields:
            self.fields["cover_image"].required = False
        if "delivery_fee" in self.fields:
            self.fields["delivery_fee"].required = False
        if "nequi_number" in self.fields:
            self.fields["nequi_number"].required = False
        if "tags" in self.fields:
            self.fields["tags"].required = False
        if "latitude" in self.fields:
            self.fields["latitude"].required = False
        if "longitude" in self.fields:
            self.fields["longitude"].required = False
        if "service_mode" in self.fields:
            self.fields["service_mode"].required = False

        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            s, e = self._parse_range_str(instance.schedule_mon)
            self.fields["mon_start"].initial = s
            self.fields["mon_end"].initial = e

            s, e = self._parse_range_str(instance.schedule_tue)
            self.fields["tue_start"].initial = s
            self.fields["tue_end"].initial = e

            s, e = self._parse_range_str(instance.schedule_wed)
            self.fields["wed_start"].initial = s
            self.fields["wed_end"].initial = e

            s, e = self._parse_range_str(instance.schedule_thu)
            self.fields["thu_start"].initial = s
            self.fields["thu_end"].initial = e

            s, e = self._parse_range_str(instance.schedule_fri)
            self.fields["fri_start"].initial = s
            self.fields["fri_end"].initial = e

            s, e = self._parse_range_str(instance.schedule_sat)
            self.fields["sat_start"].initial = s
            self.fields["sat_end"].initial = e

            s, e = self._parse_range_str(instance.schedule_sun)
            self.fields["sun_start"].initial = s
            self.fields["sun_end"].initial = e

    def clean(self):
        cleaned = super().clean()

        day_map = [
            ("Lunes", "mon_start", "mon_end"),
            ("Martes", "tue_start", "tue_end"),
            ("Miércoles", "wed_start", "wed_end"),
            ("Jueves", "thu_start", "thu_end"),
            ("Viernes", "fri_start", "fri_end"),
            ("Sábado", "sat_start", "sat_end"),
            ("Domingo", "sun_start", "sun_end"),
        ]

        for day_label, f_start, f_end in day_map:
            start = cleaned.get(f_start)
            end = cleaned.get(f_end)
            try:
                self._format_range(start, end)
            except forms.ValidationError as e:
                self.add_error(f_end, f"{day_label}: {e.messages[0]}")

        return cleaned

    def save(self, commit=True):
        instance: Business = super().save(commit=False)

        instance.schedule_mon = self._format_range(self.cleaned_data.get("mon_start"), self.cleaned_data.get("mon_end"))
        instance.schedule_tue = self._format_range(self.cleaned_data.get("tue_start"), self.cleaned_data.get("tue_end"))
        instance.schedule_wed = self._format_range(self.cleaned_data.get("wed_start"), self.cleaned_data.get("wed_end"))
        instance.schedule_thu = self._format_range(self.cleaned_data.get("thu_start"), self.cleaned_data.get("thu_end"))
        instance.schedule_fri = self._format_range(self.cleaned_data.get("fri_start"), self.cleaned_data.get("fri_end"))
        instance.schedule_sat = self._format_range(self.cleaned_data.get("sat_start"), self.cleaned_data.get("sat_end"))
        instance.schedule_sun = self._format_range(self.cleaned_data.get("sun_start"), self.cleaned_data.get("sun_end"))

        if commit:
            instance.save()
            self.save_m2m()

        return instance


class MenuCategoryForm(forms.ModelForm):
    class Meta:
        model = MenuCategory
        fields = "__all__"


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = "__all__"


class MenuFileForm(forms.ModelForm):
    class Meta:
        model = MenuFile
        fields = "__all__"