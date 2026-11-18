import pytest
from django.urls import reverse

from transporte.models import Linha, Modal

pytestmark = pytest.mark.django_db


@pytest.fixture
def linhas():
    return [
        Linha.objects.create(
            codigo=codigo,
            nome=nome,
            modal=Modal.ONIBUS,
            destino_ida=nome,
            destino_volta="Centro",
        )
        for codigo, nome in [
            ("060", "Cidade Universitária"),
            ("061", "Piedade"),
            ("062", "Centro"),
        ]
    ]


def test_busca_por_codigo_ou_nome_e_mostra_destinos(client, linhas):
    resposta = client.get(reverse("inicio"), {"q": "060"})

    assert resposta.status_code == 200
    assert b"060" in resposta.content
    assert b"Cidade Universit" in resposta.content
    assert b"061" not in resposta.content

    resposta = client.get(reverse("inicio"), {"q": "Piedade"})
    assert b"061" in resposta.content
    assert b"Centro" in resposta.content


def test_busca_sem_resultados_exibe_sugestao(client):
    resposta = client.get(reverse("inicio"), {"q": "inexistente"})

    assert resposta.status_code == 200
    assert "Nenhuma linha encontrada" in resposta.content.decode()
    assert "Tente buscar pelo número" in resposta.content.decode()


def test_linhas_mais_recentes_aparecem_primeiro(client, linhas):
    client.get(reverse("linha_status", args=[linhas[1].pk]))

    resposta = client.get(reverse("inicio"))

    conteudo = resposta.content.decode()
    assert conteudo.index("061 — Piedade") < conteudo.index("060 — Cidade")


def test_api_de_busca_retorna_modal_e_destinos(client, linhas):
    resposta = client.get(reverse("api_linhas"), {"q": "060"})

    assert resposta.status_code == 200
    assert resposta.json() == [
        {
            "id": linhas[0].pk,
            "codigo": "060",
            "nome": "Cidade Universitária",
            "modal": "onibus",
            "operadora": "",
            "destino_ida": "Cidade Universitária",
            "destino_volta": "Centro",
        }
    ]
