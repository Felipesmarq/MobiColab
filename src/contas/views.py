from django.contrib.auth import login
from django.shortcuts import redirect, render

from contas.forms import CadastroForm


def cadastro(request):
    if request.user.is_authenticated:
        return redirect("inicio")
    formulario = CadastroForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        usuario = formulario.save()
        login(request, usuario)
        return redirect("inicio")
    return render(request, "contas/cadastro.html", {"formulario": formulario})
