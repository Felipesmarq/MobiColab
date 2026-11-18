"""Regras de negócio dos relatos (spec, seção 5).

Toda decisão sobre relatos passa por este módulo; views e API são portas finas
sobre ele. Os números das regras vêm de `settings`.
"""

import math
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from relatos.models import Confirmacao, Relato
from transporte.models import Sentido


class UsuarioNaoAutenticado(Exception):
    """Visitante sem login não pode relatar (RF03). Distinta de `UsuarioBloqueado`."""


class UsuarioBloqueado(Exception):
    """Usuário bloqueado (`is_active = False`, ADR 0011) não pode relatar (RF07)."""


class RelatoInvalido(ValueError):
    """Relato fora do RN01. `args[0]` traz os erros por campo (`{campo: [mensagens]}`)."""


def registrar_relato(
    usuario,
    linha,
    sentido: str,
    lotacao: str,
    *,
    conforto_termico: str = "",
    ar_condicionado: str = "",
    vaga_pcd: str = "",
    prefixo_veiculo: str = "",
) -> Relato:
    """Valida e grava um relato (RF03, RN01) e aplica a substituição (RN05).

    Só a lotação é obrigatória. A hora do relato é a do servidor: não há parâmetro
    para o chamador informá-la.

    Se o mesmo usuário já tem um relato ativo nesta linha e sentido feito há menos de
    `RELATO_INTERVALO_MIN`, o novo o substitui: o anterior continua no banco com
    `substituido_por` preenchido (ADR 0013). Quem chama descobre isso por
    `relato.substituiu.exists()`, para avisar o usuário.

    Tudo roda numa transação que trava a linha do usuário (PostgreSQL, `READ COMMITTED`),
    então dois envios simultâneos do mesmo usuário não deixam dois relatos ativos na janela.

    Raises:
        UsuarioNaoAutenticado: visitante sem login, `None`, ou conta que já não existe.
        UsuarioBloqueado: o usuário está inativo no banco, mesmo que a instância diga ativo.
        RelatoInvalido: algum valor está fora do domínio da RN01 ou falta linha/sentido.
    """
    if usuario is None or not usuario.is_authenticated:
        raise UsuarioNaoAutenticado()
    outras_dimensoes = {
        "conforto_termico": conforto_termico,
        "ar_condicionado": ar_condicionado,
        "vaga_pcd": vaga_pcd,
        "prefixo_veiculo": prefixo_veiculo,
    }
    with transaction.atomic():
        # Trava a linha do usuário: serializa os envios dele e relê `is_active`, que a
        # instância da sessão pode ter desatualizado se a moderação bloqueou (RF07).
        # O travamento só tem efeito no PostgreSQL.
        try:
            atual = get_user_model().objects.select_for_update().get(pk=usuario.pk)
        except get_user_model().DoesNotExist:
            raise UsuarioNaoAutenticado() from None
        if not atual.is_active:
            raise UsuarioBloqueado(usuario.pk)
        return _gravar_e_substituir(usuario, linha, sentido, lotacao, outras_dimensoes)


def _gravar_e_substituir(
    usuario, linha, sentido: str, lotacao: str, outras_dimensoes: dict
) -> Relato:
    """Valida, grava e marca como substituídos os relatos ativos da janela (RN05)."""
    campos = {"sentido": sentido, "lotacao": lotacao, **outras_dimensoes}
    # `full_clean()` deixa passar `None` nos campos opcionais (blank=True) e o banco
    # recusa com IntegrityError; por isso a checagem de tipo vem antes.
    erros = {campo: ["Informe um texto."] for campo, valor in campos.items() if valor is None}
    if erros:
        raise RelatoInvalido(erros)

    agora = timezone.now()
    relato = Relato(usuario=usuario, linha=linha, criado_em=agora, **campos)
    try:
        relato.full_clean()
    except ValidationError as erro:
        raise RelatoInvalido(erro.message_dict) from erro

    relato.save()
    inicio_da_janela = agora - timedelta(minutes=settings.RELATO_INTERVALO_MIN)
    Relato.objects.filter(
        usuario=usuario,
        linha=linha,
        sentido=sentido,
        criado_em__gt=inicio_da_janela,
        substituido_por__isnull=True,
        removido_em__isnull=True,
    ).exclude(pk=relato.pk).update(substituido_por=relato)
    return relato


def confirmar_relato(usuario, relato: Relato, ainda_vale: bool) -> Confirmacao:
    """Registra um voto único em relato ativo, exceto pelo próprio autor (RF05, RN06)."""
    if usuario is None or not usuario.is_authenticated:
        raise UsuarioNaoAutenticado()
    if not isinstance(ainda_vale, bool):
        raise RelatoInvalido({"ainda_vale": ["Informe se o relato ainda vale."]})
    if not isinstance(relato, Relato) or not relato.pk:
        raise RelatoInvalido({"relato": ["Relato não encontrado."]})

    with transaction.atomic():
        try:
            atual = get_user_model().objects.select_for_update().get(pk=usuario.pk)
        except get_user_model().DoesNotExist:
            raise UsuarioNaoAutenticado() from None
        if not atual.is_active:
            raise UsuarioBloqueado(usuario.pk)

        try:
            alvo = Relato.objects.select_for_update().get(pk=relato.pk)
        except Relato.DoesNotExist:
            raise RelatoInvalido({"relato": ["Relato não encontrado."]}) from None

        agora = timezone.now()
        if alvo.usuario_id == atual.pk:
            raise RelatoInvalido({"relato": ["Você não pode votar no próprio relato."]})
        if (
            alvo.removido_em is not None
            or alvo.substituido_por_id is not None
            or alvo.criado_em < agora - timedelta(minutes=settings.RELATO_VALIDADE_MIN)
        ):
            raise RelatoInvalido({"relato": ["Este relato não está mais ativo."]})

        confirmacao, criada = Confirmacao.objects.get_or_create(
            relato=alvo,
            usuario=atual,
            defaults={"ainda_vale": ainda_vale},
        )
        if not criada:
            raise RelatoInvalido({"relato": ["Você já confirmou ou contestou este relato."]})
        return confirmacao


def status_linha(linha, sentido: str, agora: datetime | None = None) -> dict:
    """Calcula valores predominantes, contagem e idade por dimensão (RF04, RN02–RN04)."""
    erros = {}
    if linha is None or not getattr(linha, "pk", None):
        erros["linha"] = ["Informe uma linha."]
    if sentido not in Sentido.values:
        erros["sentido"] = ["Informe um sentido válido."]
    if erros:
        raise RelatoInvalido(erros)

    agora = agora or timezone.now()
    relatos = Relato.objects.filter(
        linha=linha,
        sentido=sentido,
        criado_em__gte=agora - timedelta(minutes=settings.RELATO_VALIDADE_MIN),
        substituido_por__isnull=True,
        removido_em__isnull=True,
    ).prefetch_related(
        Prefetch(
            "confirmacoes",
            queryset=Confirmacao.objects.only("relato_id", "ainda_vale", "criado_em"),
        )
    )
    por_dimensao = {
        "lotacao": {},
        "conforto_termico": {},
        "ar_condicionado": {},
        "vaga_pcd": {},
    }

    for relato in relatos:
        peso = _peso_com_confirmacoes(relato, agora, list(relato.confirmacoes.all()))
        if peso <= 0:
            continue
        for campo, totais in por_dimensao.items():
            valor = getattr(relato, campo)
            if valor:
                estatistica = totais.setdefault(
                    valor, {"peso": 0.0, "relatos": 0, "ultimo_em": relato.criado_em}
                )
                estatistica["peso"] += peso
                estatistica["relatos"] += 1
                if relato.criado_em > estatistica["ultimo_em"]:
                    estatistica["ultimo_em"] = relato.criado_em

    resultado = {}
    for campo, totais in por_dimensao.items():
        melhor_valor = max(totais, key=lambda valor: totais[valor]["peso"], default=None)
        total_peso = sum(item["peso"] for item in totais.values())
        quantidade = sum(item["relatos"] for item in totais.values())
        ultimo_em = max((item["ultimo_em"] for item in totais.values()), default=None)
        if total_peso < settings.PESO_MINIMO:
            resultado[campo] = {
                "valor": None,
                "relatos": quantidade,
                "ultimo_em": ultimo_em,
                "minutos_atras": (
                    max(0, int((agora - ultimo_em).total_seconds() // 60)) if ultimo_em else None
                ),
            }
            continue
        resultado[campo] = {
            "valor": melhor_valor,
            "relatos": quantidade,
            "ultimo_em": ultimo_em,
            "minutos_atras": max(0, int((agora - ultimo_em).total_seconds() // 60)),
        }
    return resultado


def peso_do_relato(relato: Relato, agora: datetime) -> float:
    """Peso do relato no instante `agora`, com decaimento exponencial (RN02)."""
    return _peso_com_confirmacoes(relato, agora, list(relato.confirmacoes.all()))


def _peso_com_confirmacoes(
    relato: Relato, agora: datetime, confirmacoes: list[Confirmacao]
) -> float:
    confirmadas = [voto for voto in confirmacoes if voto.ainda_vale]
    # Só confirmar renova o tempo; contestar não (RN02).
    referencia = max((voto.criado_em for voto in confirmadas), default=relato.criado_em)
    minutos = max(0.0, (agora - referencia).total_seconds() / 60)
    decaimento = math.log(2) / settings.RELATO_MEIA_VIDA_MIN
    votos = (
        1
        + settings.RELATO_PESO_CONFIRMACAO * len(confirmadas)
        - settings.RELATO_PESO_CONTESTACAO * (len(confirmacoes) - len(confirmadas))
    )
    return max(0.0, math.exp(-decaimento * minutos) * votos)
