import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from relatos.models import Lotacao, Relato
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
def usuario():
    return get_user_model().objects.create_user(
        email="passageira@exemplo.com", password="senha-forte-123"
    )


def test_envio_exige_login_e_volta_ao_formulario_depois(linha, client):
    resposta = client.get(reverse("enviar_relato", args=[linha.pk]), {"sentido": "volta"})

    assert resposta.status_code == 302
    assert resposta.headers["Location"].startswith(reverse("login"))
    assert "next=" in resposta.headers["Location"]


def test_envia_relato_com_lotacao_e_opcionais_vazios(linha, usuario, client):
    client.force_login(usuario)

    resposta = client.post(
        reverse("enviar_relato", args=[linha.pk]),
        {"sentido": "ida", "lotacao": Lotacao.LOTADO},
    )

    relato = Relato.objects.get()
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == f"{reverse('linha_status', args=[linha.pk])}?sentido=ida"
    assert relato.sentido == Sentido.IDA
    assert relato.lotacao == Lotacao.LOTADO
    assert relato.conforto_termico == ""
    assert b"Obrigado por colaborar" in client.get(resposta.headers["Location"]).content


def test_tenta_enviar_novamente_na_janela_substitui_relato(linha, usuario, client):
    client.force_login(usuario)
    endpoint = reverse("enviar_relato", args=[linha.pk])
    dados = {"sentido": "ida", "lotacao": Lotacao.VAZIO}
    client.post(endpoint, dados)

    resposta = client.post(endpoint, {**dados, "lotacao": Lotacao.LOTADO})

    anterior, novo = Relato.objects.order_by("criado_em")
    anterior.refresh_from_db()
    assert resposta.status_code == 302
    assert anterior.substituido_por == novo
    assert b"Relato atualizado" in client.get(resposta.headers["Location"]).content


def test_recusa_lotacao_invalida_sem_criar_relato(linha, usuario, client):
    client.force_login(usuario)

    resposta = client.post(
        reverse("enviar_relato", args=[linha.pk]),
        {"sentido": "ida", "lotacao": "lotado-demais"},
    )

    assert resposta.status_code == 200
    assert not Relato.objects.exists()
    assert "lotacao" in resposta.context["formulario"].errors


def test_api_de_envio_exige_login_e_retorna_relato_criado(linha, usuario, client):
    endpoint = reverse("api_relatos")
    dados = {"linha": linha.pk, "sentido": "volta", "lotacao": "moderado"}

    resposta = client.post(endpoint, dados)
    assert resposta.status_code == 401
    assert not Relato.objects.exists()

    client.force_login(usuario)
    resposta = client.post(endpoint, dados)

    assert resposta.status_code == 201
    assert resposta.json()["substituiu"] is False
    assert Relato.objects.get().sentido == Sentido.VOLTA

    resposta = client.post(endpoint, {**dados, "lotacao": "lotado"})
    assert resposta.status_code == 201
    assert resposta.json()["substituiu"] is True
    assert Relato.objects.count() == 2
