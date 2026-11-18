from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.utils import timezone

from relatos.models import Confirmacao, Lotacao, Relato
from relatos.regras import (
    RelatoInvalido,
    UsuarioBloqueado,
    UsuarioNaoAutenticado,
    confirmar_relato,
)
from transporte.models import Linha, Modal, Sentido

pytestmark = pytest.mark.django_db


@pytest.fixture
def linha():
    return Linha.objects.create(
        codigo="060",
        nome="Cidade Universitária",
        modal=Modal.ONIBUS,
        destino_ida="Cidade Universitária",
    )


@pytest.fixture
def usuarios():
    usuario = get_user_model()
    return (
        usuario.objects.create_user(email="autor@exemplo.com"),
        usuario.objects.create_user(email="votante@exemplo.com"),
    )


@pytest.fixture
def relato(linha, usuarios):
    return Relato.objects.create(
        linha=linha,
        usuario=usuarios[0],
        sentido=Sentido.IDA,
        lotacao=Lotacao.MODERADO,
    )


def test_confirma_e_contesta_com_peso_refletido(relato, usuarios):
    confirmacao = confirmar_relato(usuarios[1], relato, True)

    assert confirmacao.ainda_vale
    assert relato.confirmacoes.count() == 1
    with pytest.raises(RelatoInvalido):
        confirmar_relato(usuarios[1], relato, False)


def test_recusa_voto_anonimo_bloqueado_e_proprio_relato(relato, usuarios):
    with pytest.raises(UsuarioNaoAutenticado):
        confirmar_relato(AnonymousUser(), relato, True)

    usuarios[1].is_active = False
    usuarios[1].save()
    with pytest.raises(UsuarioBloqueado):
        confirmar_relato(usuarios[1], relato, True)

    with pytest.raises(RelatoInvalido):
        confirmar_relato(usuarios[0], relato, True)


@pytest.mark.parametrize(
    "alteracoes",
    [
        {"removido_em": timezone.now},
        {"substituido_por_id": 100000},
        {"criado_em": lambda: timezone.now() - timedelta(minutes=46)},
    ],
)
def test_recusa_voto_em_relato_inativo(relato, usuarios, alteracoes):
    valores = {chave: valor() if callable(valor) else valor for chave, valor in alteracoes.items()}
    for chave, valor in valores.items():
        setattr(relato, chave, valor)
    if "substituido_por_id" in valores:
        # A FK precisa existir antes de salvar o relato.
        substituto = Relato.objects.create(
            linha=relato.linha,
            usuario=usuarios[0],
            sentido=Sentido.VOLTA,
            lotacao=Lotacao.VAZIO,
        )
        relato.substituido_por = substituto
    relato.save()

    with pytest.raises(RelatoInvalido):
        confirmar_relato(usuarios[1], relato, True)


def test_recusa_valor_de_voto_invalido_e_alvo_ausente(relato, usuarios):
    with pytest.raises(RelatoInvalido) as erro:
        confirmar_relato(usuarios[1], relato, "sim")
    assert "ainda_vale" in erro.value.args[0]

    with pytest.raises(RelatoInvalido) as erro:
        confirmar_relato(usuarios[1], None, True)
    assert "relato" in erro.value.args[0]


def test_confirmacao_api_nao_oferece_voto_proprio_e_grava_voto(relato, usuarios, client):
    client.force_login(usuarios[0])
    resposta = client.get(reverse("linha_status", args=[relato.linha_id]))
    assert b"Seu relato" in resposta.content
    assert b"Ainda est" not in resposta.content

    client.force_login(usuarios[1])
    resposta = client.post(reverse("api_confirmacoes", args=[relato.pk]), {"ainda_vale": False})
    assert resposta.status_code == 201
    assert resposta.json()["ainda_vale"] is False
    assert Confirmacao.objects.get().ainda_vale is False


def test_tela_permite_um_voto_e_esconde_acoes_apos_confirmar(relato, usuarios, client):
    client.force_login(usuarios[1])
    resposta = client.get(reverse("linha_status", args=[relato.linha_id]))
    assert b"Ainda est" in resposta.content

    resposta = client.post(reverse("votar_relato", args=[relato.pk]), {"ainda_vale": "true"})

    assert resposta.status_code == 302
    assert resposta.headers["Location"].endswith("?sentido=ida")
    assert Confirmacao.objects.get().ainda_vale
    resposta = client.get(resposta.headers["Location"])
    assert "Você já votou neste relato" in resposta.content.decode()
    assert b"Ainda est" not in resposta.content
