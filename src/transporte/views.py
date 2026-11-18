from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, render

from transporte.models import Linha

RECENTES_NA_SESSAO = "linhas_recentes"
RECENTES_MAXIMO = 5


def inicio(request):
    termo = request.GET.get("q", "").strip()
    linhas = Linha.objects.filter(ativa=True)
    if termo:
        linhas = linhas.filter(Q(codigo__icontains=termo) | Q(nome__icontains=termo))
    recentes = request.session.get(RECENTES_NA_SESSAO, [])
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
    return render(
        request,
        "inicio.html",
        {"linhas": linhas, "termo": termo, "recentes": set(recentes)},
    )


def linha_status(request, pk):
    """Página da linha. O status agregado (RF04) entra com a issue #20."""
    linha = get_object_or_404(Linha, pk=pk, ativa=True)
    _lembrar_linha(request, linha.pk)
    return render(request, "transporte/linha.html", {"linha": linha})


def _lembrar_linha(request, pk):
    recentes = [r for r in request.session.get(RECENTES_NA_SESSAO, []) if r != pk]
    request.session[RECENTES_NA_SESSAO] = [pk, *recentes][:RECENTES_MAXIMO]
