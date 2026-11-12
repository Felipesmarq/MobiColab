"""RNF01 e RNF04: layout base mobile-first, acessível, com HTMX e Tailwind."""

import re

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def html(client):
    resposta = client.get(reverse("inicio"))
    assert resposta.status_code == 200
    return resposta.content.decode()


def test_declara_idioma_e_viewport_para_celular(html):
    assert '<html lang="pt-br"' in html
    assert 'name="viewport" content="width=device-width, initial-scale=1"' in html


def test_carrega_css_do_tailwind_e_htmx_locais(html):
    assert "/static/css/tailwind.css" in html
    assert "/static/js/htmx.min.js" in html


def test_assets_estaticos_existem_no_repositorio():
    from django.contrib.staticfiles import finders

    assert finders.find("css/tailwind.css")
    assert finders.find("js/htmx.min.js")


def test_menu_tem_item_painel_sem_destino(html):
    menu = re.search(r"<nav[^>]*aria-label=\"Principal\".*?</nav>", html, re.S)
    assert menu, "menu principal precisa de <nav aria-label='Principal'>"
    assert "Painel" in menu.group(0)
    assert 'aria-disabled="true"' in menu.group(0)


def test_tem_link_de_pular_para_o_conteudo_e_landmark_main(html):
    assert 'href="#conteudo"' in html
    assert '<main id="conteudo"' in html


def test_csrf_token_enviado_pelo_htmx(html):
    assert "X-CSRFToken" in html
