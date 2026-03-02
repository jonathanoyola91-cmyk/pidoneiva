from django import forms
from businesses.models import Business
from menu.models import MenuCategory, MenuItem, MenuFile


class BusinessForm(forms.ModelForm):
    # Campos "bonitos" (no existen en el modelo; son del form)
    mon_start = forms.TimeField(required=False, label="Lunes (inicio)", widget=forms.TimeInput(attrs={"type": "time"}))
    mon_end = forms.TimeField(required=False, label="Lunes (fin)", widget=forms.TimeInput(attrs={"type": "time"}))

    tue_start = forms.TimeField(required=False, label="Martes (inicio)", widget=forms.TimeInput(attrs={"type": "time"}))
    tue_end = forms.TimeField(required=False, label="Martes (fin)", widget=forms.TimeInput(attrs={"type": "time"}))

    wed_start = forms.TimeField(required=False, label="Miércoles (inicio)", widget=forms.TimeInput(attrs={"type": "time"}))
    wed_end = forms.TimeField(required=False, label="Miércoles (fin)", widget=forms.TimeInput(attrs={"type": "time"}))

    thu_start = forms.TimeField(required=False, label="Jueves (inicio)", widget=forms.TimeInput(attrs={"type": "time"}))
    thu_end = forms.TimeField(required=False, label="Jueves (fin)", widget=forms.TimeInput(attrs={"type": "time"}))

    fri_start = forms.TimeField(required=False, label="Viernes (inicio)", widget=forms.TimeInput(attrs={"type": "time"}))
    fri_end = forms.TimeField(required=False, label="Viernes (fin)", widget=forms.TimeInput(attrs={"type": "time"}))

    sat_start = forms.TimeField(required=False, label="Sábado (inicio)", widget=forms.TimeInput(attrs={"type": "time"}))
    sat_end = forms.TimeField(required=False, label="Sábado (fin)", widget=forms.TimeInput(attrs={"type": "time"}))

    sun_start = forms.TimeField(required=False, label="Domingo (inicio)", widget=forms.TimeInput(attrs={"type": "time"}))
    sun_end = forms.TimeField(required=False, label="Domingo (fin)", widget=forms.TimeInput(attrs={"type": "time"}))

    class Meta:
        model = Business
        fields = [
            "name", "business_type", "menu_mode", "zone", "address",
            "phone", "whatsapp", "instagram", "description",
            "tags",          # ✅ NUEVO: para que el dueño lo diligencie
            "logo",

            # switch de pedidos
            "is_accepting_orders",

            # OJO: NO incluimos schedule_* aquí porque NO se escribirán manualmente
            # Se llenan desde los campos mon_start/mon_end etc. en save().
        ]

        labels = {
            "is_accepting_orders": "Estoy recibiendo pedidos",
            "tags": "Etiquetas (tags)",
        }

        help_texts = {
            "tags": "Separa por coma. Ej: pizza, hamburguesa, café, droguería, mercado",
        }

    # ---------- Helpers ----------
    def _format_range(self, start, end) -> str:
        """Convierte dos datetime.time a 'HH:MM-HH:MM'. Si ambos vacíos -> ''."""
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
        """Lee 'HH:MM-HH:MM' y devuelve (time_start, time_end) o (None, None)."""
        s = (s or "").strip()
        if not s or "-" not in s:
            return None, None
        a, b = s.split("-", 1)
        a = a.strip()
        b = b.strip()
        try:
            sh, sm = [int(x) for x in a.split(":")]
            eh, em = [int(x) for x in b.split(":")]
            # no usamos datetime.time import aquí; Django devuelve time objects en TimeField igual
            from datetime import time as dt_time
            return dt_time(sh, sm), dt_time(eh, em)
        except Exception:
            return None, None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ UI del campo tags (placeholder + clase)
        if "tags" in self.fields:
            self.fields["tags"].required = False
            self.fields["tags"].widget.attrs.update({
                "placeholder": "Ej: pizza, hamburguesa, café, droguería, mercado",
            })
            # si usas Bootstrap en dashboard, ayuda a que se vea bien:
            existing_class = self.fields["tags"].widget.attrs.get("class", "")
            self.fields["tags"].widget.attrs["class"] = (existing_class + " form-control").strip()

        # Pre-cargar el form desde el modelo (editar negocio)
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            # Lunes
            s, e = self._parse_range_str(instance.schedule_mon)
            self.fields["mon_start"].initial = s
            self.fields["mon_end"].initial = e

            # Martes
            s, e = self._parse_range_str(instance.schedule_tue)
            self.fields["tue_start"].initial = s
            self.fields["tue_end"].initial = e

            # Miércoles
            s, e = self._parse_range_str(instance.schedule_wed)
            self.fields["wed_start"].initial = s
            self.fields["wed_end"].initial = e

            # Jueves
            s, e = self._parse_range_str(instance.schedule_thu)
            self.fields["thu_start"].initial = s
            self.fields["thu_end"].initial = e

            # Viernes
            s, e = self._parse_range_str(instance.schedule_fri)
            self.fields["fri_start"].initial = s
            self.fields["fri_end"].initial = e

            # Sábado
            s, e = self._parse_range_str(instance.schedule_sat)
            self.fields["sat_start"].initial = s
            self.fields["sat_end"].initial = e

            # Domingo
            s, e = self._parse_range_str(instance.schedule_sun)
            self.fields["sun_start"].initial = s
            self.fields["sun_end"].initial = e

    def clean(self):
        cleaned = super().clean()

        # Validar y construir rangos (permitimos cruce de medianoche: start > end)
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
                # asignamos error al campo de fin (se ve claro)
                self.add_error(f_end, f"{day_label}: {e.messages[0]}")

        return cleaned

    def save(self, commit=True):
        instance: Business = super().save(commit=False)

        # Construir strings schedule_* desde los time inputs
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
        fields = ["name", "order"]


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ["category", "name", "description", "price", "photo", "is_available", "order"]


class MenuFileForm(forms.ModelForm):
    class Meta:
        model = MenuFile
        fields = ["file", "is_active"]