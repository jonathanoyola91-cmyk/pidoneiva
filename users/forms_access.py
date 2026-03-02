from django import forms
from .models import AccessRequest

ZONE_CHOICES = [
    ("SUR", "Sur"),
    ("NORTE", "Norte"),
    ("ORIENTE", "Oriente"),
    ("CENTRO", "Centro"),
]


class AccessRequestForm(forms.ModelForm):
    # ✅ Forzar dropdown de zona (aunque el modelo sea CharField)
    zone = forms.ChoiceField(
        choices=[("", "Selecciona una zona")] + ZONE_CHOICES,
        required=False,
        label="Zona",
    )

    class Meta:
        model = AccessRequest
        fields = [
            "name",
            "request_type",
            "zone",
            "address",
            "contact_name",
            "whatsapp",
            "email",
            "notes",
        ]

        labels = {
            "name": "Nombre del negocio",
            "request_type": "Tipo de solicitud",
            "address": "Dirección",
            "contact_name": "Nombre de contacto",
            "whatsapp": "WhatsApp",
            "email": "Correo electrónico",
            "notes": "Notas adicionales",
        }

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Hamburguesas Don Pepe",
            }),
            "request_type": forms.Select(attrs={
                "class": "form-select",
            }),
            "address": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Cra 5 # 12-34",
            }),
            "contact_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Juan Pérez",
            }),
            "whatsapp": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: 57 3101234567",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: negocio@email.com",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Cuéntanos qué vendes, horarios, si tienes domicilio, etc.",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Aplicar estilo Bootstrap al campo zone (ChoiceField)
        self.fields["zone"].widget.attrs.update({
            "class": "form-select",
        })

        # ✅ Si quieres: dejar WhatsApp solo números/espacios visualmente (no valida, solo ayuda)
        self.fields["whatsapp"].widget.attrs.update({
            "inputmode": "numeric",
        })