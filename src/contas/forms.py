from django import forms
from django.contrib.auth.forms import UserCreationForm

from contas.models import Usuario


class CadastroForm(UserCreationForm):
    def clean_email(self):
        email = Usuario.objects.normalize_email(self.cleaned_data["email"].strip())
        # normalize_email só põe o domínio em minúsculas; sem isto, "Ana@x.com" e
        # "ana@x.com" virariam duas contas.
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email

    class Meta:
        model = Usuario
        fields = ("email",)
