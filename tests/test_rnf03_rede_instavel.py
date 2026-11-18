"""RNF03 — com conexão instável, o envio falha com mensagem clara e o formulário
mantém o que foi preenchido (issue #16).

O lado do navegador (falha de rede e timeout) é tratado em `envio-relato.js`:
o envio vai por HTMX, então uma falha não recarrega a página e os campos ficam
como estavam. Aqui se testa o contrato com o servidor.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from relatos.models import Relato
from transporte.models import Linha, Modal

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def linha():
    return Linha.objects.create(
        codigo="060", nome="Cidade Universitária", modal=Modal.ONIBUS, destino_ida="CDU"
    )


@pytest.fixture
def logado(client):
    usuario = get_user_model().objects.create_user(email="ana@exemplo.com", password="x")
    client.force_login(usuario)
    return client


def test_formulario_envia_por_htmx_com_timeout_e_aviso_de_falha(linha, logado):
    pagina = logado.get(reverse("enviar_relato", args=[linha.pk])).content.decode()

    assert 'id="formulario-relato"' in pagina
    assert "hx-post=" in pagina
    assert '"timeout"' in pagina
    assert 'id="erro-envio"' in pagina
    assert "js/envio-relato.js" in pagina


def test_envio_por_htmx_bem_sucedido_redireciona_pelo_cabecalho(linha, logado):
    resposta = logado.post(
        reverse("enviar_relato", args=[linha.pk]),
        {"sentido": "ida", "lotacao": "lotado"},
        **HTMX,
    )

    assert resposta.status_code == 200
    assert resposta.headers["HX-Redirect"] == (
        reverse("linha_status", args=[linha.pk]) + "?sentido=ida"
    )
    assert Relato.objects.count() == 1


def test_envio_por_htmx_invalido_devolve_o_formulario_preenchido(linha, logado):
    resposta = logado.post(
        reverse("enviar_relato", args=[linha.pk]),
        {"sentido": "ida", "lotacao": "", "prefixo_veiculo": "12345"},
        **HTMX,
    )

    pagina = resposta.content.decode()
    assert resposta.status_code == 200
    assert "HX-Redirect" not in resposta.headers
    assert 'value="12345"' in pagina
    assert 'role="alert"' in pagina
    assert not Relato.objects.exists()


def test_comentario_do_template_nao_aparece_na_pagina(linha, logado):
    pagina = logado.get(reverse("enviar_relato", args=[linha.pk])).content.decode()
    assert "RNF03" not in pagina
