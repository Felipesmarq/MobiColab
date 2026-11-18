from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode

from relatos.forms import FormularioRelato
from relatos.models import (
    ArCondicionado,
    Confirmacao,
    ConfortoTermico,
    Lotacao,
    Relato,
    VagaPcd,
)
from relatos.regras import (
    RelatoInvalido,
    UsuarioBloqueado,
    UsuarioNaoAutenticado,
    confirmar_relato,
    registrar_relato,
    status_linha,
)
from transporte.models import Linha, Sentido


def _adicionar_linha_recente(request, linha):
    recentes = [linha.pk, *request.session.get("linhas_recentes", [])]
    request.session["linhas_recentes"] = list(dict.fromkeys(recentes))[:5]


def status_da_linha(request, pk):
    linha = get_object_or_404(Linha, pk=pk, ativa=True)
    sentido = request.GET.get("sentido", Sentido.IDA)
    if sentido not in Sentido.values:
        sentido = Sentido.IDA
    _adicionar_linha_recente(request, linha)

    agora = timezone.now()
    status = status_linha(linha, sentido, agora)
    relatos = (
        Relato.objects.filter(
            linha=linha,
            sentido=sentido,
            criado_em__gte=agora - timedelta(minutes=settings.RELATO_VALIDADE_MIN),
            substituido_por__isnull=True,
            removido_em__isnull=True,
        )
        .select_related("usuario")
        .order_by("-criado_em")[:10]
    )
    if request.user.is_authenticated:
        relatos = relatos.annotate(
            votou=Exists(Confirmacao.objects.filter(relato_id=OuterRef("pk"), usuario=request.user))
        )
    configuracoes = [
        ("lotacao", "Lotação", dict(Lotacao.choices)),
        ("conforto_termico", "Conforto térmico", dict(ConfortoTermico.choices)),
        ("ar_condicionado", "Ar-condicionado", dict(ArCondicionado.choices)),
        ("vaga_pcd", "Vaga PCD", dict(VagaPcd.choices)),
    ]
    dimensoes = [
        {
            "nome": nome,
            "valor": valores.get(item["valor"], "Sem informação recente"),
            "relatos": item["relatos"],
            "minutos_atras": item["minutos_atras"],
        }
        for campo, nome, valores in configuracoes
        for item in [status[campo]]
    ]
    return render(
        request,
        "relatos/status_linha.html",
        {
            "linha": linha,
            "sentido": sentido,
            "sentidos": Sentido.choices,
            "dimensoes": dimensoes,
            "relatos": relatos,
            "agora": agora,
        },
    )


@login_required
def enviar_relato(request, pk):
    linha = get_object_or_404(Linha, pk=pk, ativa=True)
    if request.method == "POST":
        formulario = FormularioRelato(request.POST)
        if formulario.is_valid():
            try:
                dados = formulario.cleaned_data.copy()
                sentido = dados.pop("sentido")
                relato = registrar_relato(request.user, linha, sentido, **dados)
            except RelatoInvalido as erro:
                for campo, mensagens in erro.args[0].items():
                    for mensagem in mensagens:
                        formulario.add_error(
                            campo if campo in formulario.fields else None, mensagem
                        )
            except UsuarioNaoAutenticado:
                messages.error(request, "Entre na sua conta para enviar um relato.")
                return redirect("login")
            except UsuarioBloqueado:
                messages.error(request, "Sua conta está bloqueada e não pode enviar relatos.")
            else:
                _adicionar_linha_recente(request, linha)
                if relato.substituiu.exists():
                    messages.success(request, "Relato atualizado. Obrigado por colaborar!")
                else:
                    messages.success(request, "Obrigado por colaborar!")
                destino = reverse("linha_status", args=[linha.pk])
                return redirect(f"{destino}?{urlencode({'sentido': relato.sentido})}")
    else:
        sentido = request.GET.get("sentido", Sentido.IDA)
        if sentido not in Sentido.values:
            sentido = Sentido.IDA
        formulario = FormularioRelato(initial={"sentido": sentido})
    return render(
        request,
        "relatos/enviar_relato.html",
        {"formulario": formulario, "linha": linha},
    )


@login_required
def votar_relato(request, pk):
    if request.method != "POST":
        return redirect("inicio")
    relato = get_object_or_404(Relato.objects.select_related("linha"), pk=pk)
    try:
        valor = request.POST.get("ainda_vale", "")
        if valor not in ("true", "false"):
            raise RelatoInvalido({"ainda_vale": ["Selecione uma opção válida."]})
        confirmacao = confirmar_relato(request.user, relato, valor == "true")
    except RelatoInvalido as erro:
        messages.error(request, next(iter(erro.args[0].values()))[0])
    except UsuarioNaoAutenticado:
        messages.error(request, "Entre na sua conta para votar.")
        return redirect("login")
    except UsuarioBloqueado:
        messages.error(request, "Sua conta está bloqueada e não pode votar.")
    else:
        voto = "confirmado" if confirmacao.ainda_vale else "contestado"
        messages.success(request, f"Relato {voto}. Obrigado por colaborar!")
    destino = reverse("linha_status", args=[relato.linha_id])
    return redirect(f"{destino}?{urlencode({'sentido': relato.sentido})}")
