from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from relatos.models import Confirmacao, Lotacao, Relato
from relatos.regras import RelatoInvalido, status_linha
from transporte.models import Linha, Modal, Sentido

pytestmark = pytest.mark.django_db


@pytest.fixture
def linha():
    return Linha.objects.create(
        codigo="060",
        nome="Cidade Universitária",
        modal=Modal.ONIBUS,
        destino_ida="Cidade Universitária",
        destino_volta="Centro",
    )


@pytest.fixture
def autor():
    return get_user_model().objects.create_user(email="autor@exemplo.com")


@pytest.fixture
def agora(monkeypatch):
    instante = timezone.now()
    monkeypatch.setattr(timezone, "now", lambda: instante)
    return instante


def criar_relato(linha, autor, criado_em, lotacao, **campos):
    return Relato.objects.create(
        linha=linha,
        usuario=autor,
        sentido=Sentido.IDA,
        criado_em=criado_em,
        lotacao=lotacao,
        **campos,
    )


def test_status_pesa_recencia_e_confirmacoes(linha, autor, agora):
    recente = criar_relato(linha, autor, agora - timedelta(minutes=10), Lotacao.VAZIO)
    antigo = criar_relato(linha, autor, agora, Lotacao.LOTADO)
    votantes = [get_user_model().objects.create_user(email=f"v{i}@exemplo.com") for i in range(2)]
    for votante in votantes:
        Confirmacao.objects.create(relato=antigo, usuario=votante, ainda_vale=True)

    resultado = status_linha(linha, Sentido.IDA, agora)

    assert resultado["lotacao"]["valor"] == Lotacao.LOTADO
    assert resultado["lotacao"]["relatos"] == 2
    assert resultado["lotacao"]["minutos_atras"] == 0
    assert resultado["conforto_termico"]["valor"] is None
    assert resultado["conforto_termico"]["relatos"] == 0
    assert recente.pk != antigo.pk


def test_status_ignora_expirados_substituidos_e_removidos(linha, autor, agora, settings):
    settings.RELATO_VALIDADE_MIN = 45
    expirado = criar_relato(linha, autor, agora - timedelta(minutes=46), Lotacao.LOTADO)
    substituido = criar_relato(linha, autor, agora, Lotacao.VAZIO, substituido_por=expirado)
    criar_relato(linha, autor, agora, Lotacao.MODERADO, removido_em=agora)

    resultado = status_linha(linha, Sentido.IDA, agora)

    assert resultado["lotacao"]["valor"] is None
    assert resultado["lotacao"]["relatos"] == 0
    assert substituido.substituido_por == expirado


def test_limite_de_peso_mostra_sem_informacao_sem_esconder_contagem(linha, autor, agora, settings):
    settings.PESO_MINIMO = 2
    criar_relato(linha, autor, agora, Lotacao.VAZIO)

    resultado = status_linha(linha, Sentido.IDA, agora)

    assert resultado["lotacao"]["valor"] is None
    assert resultado["lotacao"]["relatos"] == 1
    assert resultado["lotacao"]["minutos_atras"] == 0


def test_status_sem_relatos_tem_idade_vazia(linha, agora):
    resultado = status_linha(linha, Sentido.VOLTA, agora)

    assert resultado["lotacao"] == {
        "valor": None,
        "relatos": 0,
        "ultimo_em": None,
        "minutos_atras": None,
    }


def test_status_recusa_linha_ou_sentido_invalidos():
    with pytest.raises(RelatoInvalido) as erro:
        status_linha(None, "norte")

    assert set(erro.value.args[0]) == {"linha", "sentido"}


def test_status_e_publico_e_exige_sentido_valido(linha, client):
    resposta = client.get(reverse("api_status_linha", args=[linha.pk]), {"sentido": "norte"})

    assert resposta.status_code == 400
    assert "sentido" in resposta.json()

    resposta = client.get(reverse("api_status_linha", args=[linha.pk]))
    assert resposta.status_code == 200
    assert resposta.json()["dimensoes"]["lotacao"]["valor"] is None


def test_tela_publica_mostra_status_sem_dados(linha, client):
    resposta = client.get(reverse("linha_status", args=[linha.pk]))

    assert resposta.status_code == 200
    assert "Sem informação recente" in resposta.content.decode()
    assert "Cidade Universitária" in resposta.content.decode()
