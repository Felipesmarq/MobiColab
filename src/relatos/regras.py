"""Regras de negócio dos relatos (spec, seção 5).

Toda decisão sobre relatos passa por este módulo; views e API são portas finas
sobre ele. Os números das regras vêm de `settings`.
"""

import math

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.utils import timezone

from relatos.models import Relato


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
    """Valida e grava um relato (RF03, RN01).

    Só a lotação é obrigatória. A hora do relato é a do servidor: não há parâmetro
    para o chamador informá-la.

    Raises:
        UsuarioNaoAutenticado: visitante sem login ou usuário ausente.
        UsuarioBloqueado: o usuário está inativo.
        RelatoInvalido: algum valor está fora do domínio da RN01 ou falta linha/sentido.
    """
    if usuario is None or not usuario.is_authenticated:
        raise UsuarioNaoAutenticado()
    if not usuario.is_active:
        raise UsuarioBloqueado(usuario.pk)

    textos = {
        "sentido": sentido,
        "lotacao": lotacao,
        "conforto_termico": conforto_termico,
        "ar_condicionado": ar_condicionado,
        "vaga_pcd": vaga_pcd,
        "prefixo_veiculo": prefixo_veiculo,
    }
    # `full_clean()` deixa passar `None` nos campos opcionais (blank=True) e o banco
    # recusa com IntegrityError; por isso a checagem de tipo vem antes.
    erros = {campo: ["Informe um texto."] for campo, valor in textos.items() if valor is None}
    if erros:
        raise RelatoInvalido(erros)

    relato = Relato(
        usuario=usuario,
        linha=linha,
        criado_em=timezone.now(),
        **textos,
    )
    try:
        relato.full_clean()
    except ValidationError as erro:
        raise RelatoInvalido(erro.message_dict) from erro

    relato.save()
    return relato


def peso_do_relato(relato: Relato, agora) -> float:
    """Peso do relato no instante `agora`, com decaimento exponencial (RN02)."""
    confirmadas = relato.confirmacoes.filter(ainda_vale=True)
    # Só confirmar renova o tempo; contestar não (RN02).
    referencia = confirmadas.aggregate(ultima=Max("criado_em"))["ultima"] or relato.criado_em
    minutos = (agora - referencia).total_seconds() / 60
    decaimento = math.log(2) / settings.RELATO_MEIA_VIDA_MIN
    confirmacoes = confirmadas.count()
    contestacoes = relato.confirmacoes.filter(ainda_vale=False).count()
    votos = (
        1
        + settings.RELATO_PESO_CONFIRMACAO * confirmacoes
        - settings.RELATO_PESO_CONTESTACAO * contestacoes
    )
    return max(0.0, math.exp(-decaimento * minutos) * votos)
