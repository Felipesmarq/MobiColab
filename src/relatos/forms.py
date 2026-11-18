from django import forms

from relatos.models import ArCondicionado, ConfortoTermico, Lotacao, VagaPcd
from transporte.models import Sentido


class FormularioRelato(forms.Form):
    sentido = forms.ChoiceField(choices=Sentido.choices, widget=forms.HiddenInput)
    lotacao = forms.ChoiceField(
        label="Lotação",
        choices=[("", "Selecione a lotação"), *Lotacao.choices],
        widget=forms.Select(
            attrs={"class": "mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2"}
        ),
    )
    conforto_termico = forms.ChoiceField(
        label="Conforto térmico",
        choices=[("", "Não informar"), *ConfortoTermico.choices],
        required=False,
        widget=forms.Select(
            attrs={"class": "mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2"}
        ),
    )
    ar_condicionado = forms.ChoiceField(
        label="Ar-condicionado",
        choices=[("", "Não informar"), *ArCondicionado.choices],
        required=False,
        widget=forms.Select(
            attrs={"class": "mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2"}
        ),
    )
    vaga_pcd = forms.ChoiceField(
        label="Vaga PCD",
        choices=[("", "Não informar"), *VagaPcd.choices],
        required=False,
        widget=forms.Select(
            attrs={"class": "mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2"}
        ),
    )
    prefixo_veiculo = forms.CharField(
        label="Prefixo do veículo (opcional)",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2",
                "autocomplete": "off",
            }
        ),
    )
