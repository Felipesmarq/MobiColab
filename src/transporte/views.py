from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import render

from transporte.models import Linha


def inicio(request):
    termo = request.GET.get("q", "").strip()
    linhas = Linha.objects.filter(ativa=True)
    if termo:
        linhas = linhas.filter(Q(codigo__icontains=termo) | Q(nome__icontains=termo))
    recentes = request.session.get("linhas_recentes", [])
    if recentes:
        linhas = linhas.order_by(
            Case(
                *[When(pk=pk, then=Value(indice)) for indice, pk in enumerate(recentes)],
                default=Value(len(recentes)),
                output_field=IntegerField(),
            ),
            "codigo",
        )
    else:
        linhas = linhas.order_by("codigo")
    return render(request, "inicio.html", {"linhas": linhas, "termo": termo})
