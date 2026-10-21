"""Testes da fase 0: models, restrições do banco, fixture e Admin (spec, seção 7).

Os testes de aceite dos RF entram na fase 1, um arquivo por RF.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import IntegrityError
from django.urls import reverse

from relatos.models import Confirmacao, Lotacao, Relato
from transporte.modais import modal_do_gtfs
from transporte.models import Linha, LinhaParada, Modal, Parada, Sentido

pytestmark = pytest.mark.django_db

Usuario = get_user_model()


@pytest.fixture
def usuario():
    return Usuario.objects.create_user(email="passageira@exemplo.com", password="senha-forte-123")


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
def parada():
    return Parada.objects.create(nome="Parada teste", lat="-8.050000", lon="-34.900000")


# Usuário (ADR 0010 e 0011)


def test_usuario_entra_por_email_sem_username(usuario):
    assert Usuario.USERNAME_FIELD == "email"
    assert not hasattr(usuario, "username") or usuario.username is None
    assert usuario.check_password("senha-forte-123")
    assert not usuario.is_staff


def test_email_e_normalizado_e_unico(usuario):
    assert Usuario.objects.create_user(email="Outra@EXEMPLO.com").email == "Outra@exemplo.com"
    with pytest.raises(IntegrityError):
        Usuario.objects.create_user(email="passageira@exemplo.com")


def test_criar_usuario_sem_email_falha():
    with pytest.raises(ValueError):
        Usuario.objects.create_user(email="")


def test_superusuario_e_staff():
    admin = Usuario.objects.create_superuser(email="admin@exemplo.com", password="x")
    assert admin.is_staff and admin.is_superuser


def test_grupo_analistas_existe():
    assert Group.objects.filter(name="analistas").exists()


# Transporte (ADR 0012)


def test_destino_por_sentido(linha):
    assert linha.destino(Sentido.IDA) == "Cidade Universitária"
    assert linha.destino(Sentido.VOLTA) == "Centro"
    assert not linha.eh_circular


def test_linha_circular_usa_destino_da_ida():
    circular = Linha.objects.create(
        codigo="101", nome="Circular", modal=Modal.ONIBUS, destino_ida="Centro"
    )
    assert circular.eh_circular
    assert circular.destino(Sentido.VOLTA) == "Centro"


def test_codigo_da_linha_e_unico(linha):
    with pytest.raises(IntegrityError):
        Linha.objects.create(codigo="060", nome="Outra", modal=Modal.ONIBUS, destino_ida="X")


def test_gtfs_route_id_vazio_pode_repetir_preenchido_nao(linha):
    Linha.objects.create(codigo="061", nome="A", modal=Modal.ONIBUS, destino_ida="A")
    Linha.objects.filter(codigo="060").update(gtfs_route_id="R1")
    with pytest.raises(IntegrityError):
        Linha.objects.create(
            codigo="062", nome="B", modal=Modal.ONIBUS, destino_ida="B", gtfs_route_id="R1"
        )


def test_parada_conhece_as_linhas_que_passam(linha, parada):
    LinhaParada.objects.create(linha=linha, parada=parada, sentido=Sentido.IDA, ordem=1)
    assert list(parada.linhas.all()) == [linha]
    assert list(linha.paradas.all()) == [parada]


def test_ordem_no_itinerario_e_unica_por_sentido(linha, parada):
    outra = Parada.objects.create(nome="Outra", lat="-8.0", lon="-34.9")
    LinhaParada.objects.create(linha=linha, parada=parada, sentido=Sentido.IDA, ordem=1)
    LinhaParada.objects.create(linha=linha, parada=parada, sentido=Sentido.VOLTA, ordem=1)
    with pytest.raises(IntegrityError):
        LinhaParada.objects.create(linha=linha, parada=outra, sentido=Sentido.IDA, ordem=1)


def test_parada_aparece_uma_vez_por_sentido(linha, parada):
    LinhaParada.objects.create(linha=linha, parada=parada, sentido=Sentido.IDA, ordem=1)
    with pytest.raises(IntegrityError):
        LinhaParada.objects.create(linha=linha, parada=parada, sentido=Sentido.IDA, ordem=2)


@pytest.mark.parametrize(
    ("route_type", "modal"), [(1, Modal.METRO), (2, Modal.METRO), (3, Modal.ONIBUS), (4, None)]
)
def test_modal_do_gtfs(route_type, modal):
    assert modal_do_gtfs(route_type) == modal


# Relatos (RN01, RN05, RN06, RN07)


def test_relato_so_com_lotacao_e_aceito(usuario, linha):
    relato = Relato.objects.create(
        usuario=usuario, linha=linha, sentido=Sentido.IDA, lotacao=Lotacao.LOTADO
    )
    assert relato.criado_em is not None
    assert not relato.removido


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("lotacao", "cheio"),
        ("conforto_termico", "morno"),
        ("ar_condicionado", "talvez"),
        ("vaga_pcd", "sim"),
        ("sentido", "norte"),
    ],
)
def test_banco_recusa_valor_fora_da_rn01(usuario, linha, campo, valor):
    dados = {"usuario": usuario, "linha": linha, "sentido": Sentido.IDA, "lotacao": Lotacao.VAZIO}
    dados[campo] = valor
    with pytest.raises(IntegrityError):
        Relato.objects.create(**dados)


def test_substituicao_preserva_o_relato_anterior(usuario, linha):
    antigo = Relato.objects.create(
        usuario=usuario, linha=linha, sentido=Sentido.IDA, lotacao=Lotacao.VAZIO
    )
    novo = Relato.objects.create(
        usuario=usuario, linha=linha, sentido=Sentido.IDA, lotacao=Lotacao.LOTADO
    )
    antigo.substituido_por = novo
    antigo.save()
    assert Relato.objects.count() == 2
    assert list(novo.substituiu.all()) == [antigo]


def test_confirmacao_e_unica_por_usuario(usuario, linha):
    autor = Usuario.objects.create_user(email="autor@exemplo.com")
    relato = Relato.objects.create(
        usuario=autor, linha=linha, sentido=Sentido.IDA, lotacao=Lotacao.MODERADO
    )
    Confirmacao.objects.create(relato=relato, usuario=usuario, ainda_vale=True)
    with pytest.raises(IntegrityError):
        Confirmacao.objects.create(relato=relato, usuario=usuario, ainda_vale=False)


# Fixture, Admin e saúde


def test_fixture_de_desenvolvimento_carrega():
    call_command("loaddata", "linhas_dev", verbosity=0)
    assert Linha.objects.count() == 5
    assert set(Linha.objects.values_list("modal", flat=True)) == {
        Modal.ONIBUS,
        Modal.BRT,
        Modal.METRO,
    }
    santa_rita = Parada.objects.get(nome="Terminal Cais de Santa Rita")
    # Cada linha passa nos dois sentidos, então aparece duas vezes no itinerário.
    assert santa_rita.linhas.distinct().count() == 3


@pytest.mark.parametrize(
    "url",
    [
        "admin:contas_usuario_changelist",
        "admin:contas_usuario_add",
        "admin:transporte_linha_changelist",
        "admin:transporte_linha_add",
        "admin:transporte_parada_changelist",
        "admin:relatos_relato_changelist",
        "admin:relatos_confirmacao_changelist",
    ],
)
def test_paginas_do_admin_abrem(client, url):
    call_command("loaddata", "linhas_dev", verbosity=0)
    admin = Usuario.objects.create_superuser(email="admin@exemplo.com", password="x")
    autor = Usuario.objects.create_user(email="autor@exemplo.com")
    relato = Relato.objects.create(
        usuario=autor, linha=Linha.objects.first(), sentido=Sentido.IDA, lotacao=Lotacao.LOTADO
    )
    Confirmacao.objects.create(relato=relato, usuario=admin, ainda_vale=False)
    client.force_login(admin)
    assert client.get(reverse(url)).status_code == 200


def test_saude(client):
    resposta = client.get(reverse("saude"))
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
