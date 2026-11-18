from django.contrib.auth.forms import UserCreationForm

from contas.models import Usuario


class CadastroForm(UserCreationForm):
    def clean_email(self):
        return Usuario.objects.normalize_email(self.cleaned_data["email"].strip())

    class Meta:
        model = Usuario
        fields = ("email",)
