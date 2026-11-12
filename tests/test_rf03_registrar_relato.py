"""RF03 — `registrar_relato` valida e grava o relato (issue #12; RN01, RF07)."""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from relatos.models import ArCondicionado, ConfortoTermico, Lotacao, Relato, VagaPcd
from relatos.regras import (
    RelatoInvalido,
    UsuarioBloqueado,
    UsuarioNaoAutenticado,
    registrar_relato,
)
from transporte.models import Linha, Modal, Sentido

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


def test_aceita_relato_so_com_lotacao(usuario, linha):
    relato = registrar_relato(usuario, linha, Sentido.IDA, Lotacao.MODERADO)

    assert Relato.objects.get() == relato
    assert relato.usuario == usuario
    assert relato.linha == linha
    assert relato.sentido == Sentido.IDA
    assert relato.lotacao == Lotacao.MODERADO
    assert relato.conforto_termico == ""
    assert relato.ar_condicionado == ""
    assert relato.vaga_pcd == ""
    assert relato.prefixo_veiculo == ""


def test_aceita_relato_com_todas_as_dimensoes(usuario, linha):
    relato = registrar_relato(
        usuario,
        linha,
        Sentido.VOLTA,
        Lotacao.LOTADO,
        conforto_termico=ConfortoTermico.QUENTE,
        ar_condicionado=ArCondicionado.NAO_FUNCIONANDO,
        vaga_pcd=VagaPcd.OCUPADA,
        prefixo_veiculo="12345",
    )

    relato.refresh_from_db()
    assert relato.conforto_termico == ConfortoTermico.QUENTE
    assert relato.ar_condicionado == ArCondicionado.NAO_FUNCIONANDO
    assert relato.vaga_pcd == VagaPcd.OCUPADA
    assert relato.prefixo_veiculo == "12345"


def test_recusa_relato_sem_lotacao(usuario, linha):
    with pytest.raises(RelatoInvalido):
        registrar_relato(usuario, linha, Sentido.IDA, "")

    assert not Relato.objects.exists()


@pytest.mark.parametrize(
    "campo",
    ["lotacao", "conforto_termico", "ar_condicionado", "vaga_pcd"],
)
def test_recusa_valor_fora_do_dominio(usuario, linha, campo):
    valores = {"lotacao": Lotacao.VAZIO, campo: "valor-inexistente"}

    with pytest.raises(RelatoInvalido) as erro:
        registrar_relato(usuario, linha, Sentido.IDA, **valores)

    assert campo in erro.value.args[0]
    assert not Relato.objects.exists()


@pytest.mark.parametrize(
    "campo",
    ["conforto_termico", "ar_condicionado", "vaga_pcd", "prefixo_veiculo"],
)
def test_recusa_none_nos_campos_opcionais(usuario, linha, campo):
    """`None` (ex.: `null` num JSON) não pode chegar ao banco como IntegrityError."""
    with pytest.raises(RelatoInvalido) as erro:
        registrar_relato(usuario, linha, Sentido.IDA, Lotacao.VAZIO, **{campo: None})

    assert campo in erro.value.args[0]
    assert not Relato.objects.exists()


def test_recusa_prefixo_acima_do_tamanho_maximo(usuario, linha):
    with pytest.raises(RelatoInvalido) as erro:
        registrar_relato(usuario, linha, Sentido.IDA, Lotacao.VAZIO, prefixo_veiculo="9" * 21)

    assert "prefixo_veiculo" in erro.value.args[0]
    assert not Relato.objects.exists()


def test_recusa_usuario_bloqueado_e_nao_grava(usuario, linha):
    usuario.is_active = False
    usuario.save()

    with pytest.raises(UsuarioBloqueado):
        registrar_relato(usuario, linha, Sentido.IDA, Lotacao.VAZIO)

    assert not Relato.objects.exists()


def test_recusa_visitante_nao_logado_como_nao_autenticado(linha):
    """Visitante não é usuário bloqueado: a API precisa distinguir 401 de 403."""
    with pytest.raises(UsuarioNaoAutenticado) as erro:
        registrar_relato(AnonymousUser(), linha, Sentido.IDA, Lotacao.VAZIO)

    assert not isinstance(erro.value, UsuarioBloqueado)
    assert not Relato.objects.exists()


def test_recusa_usuario_ausente_como_nao_autenticado(linha):
    with pytest.raises(UsuarioNaoAutenticado):
        registrar_relato(None, linha, Sentido.IDA, Lotacao.VAZIO)

    assert not Relato.objects.exists()


def test_hora_do_relato_vem_do_servidor(usuario, linha):
    antes = timezone.now()

    relato = registrar_relato(usuario, linha, Sentido.IDA, Lotacao.VAZIO)

    assert antes <= relato.criado_em <= timezone.now()


def test_nao_aceita_hora_enviada_pelo_chamador(usuario, linha):
    with pytest.raises(TypeError):
        registrar_relato(usuario, linha, Sentido.IDA, Lotacao.VAZIO, criado_em=timezone.now())


@pytest.mark.parametrize("sentido", ["", "lado-errado", None])
def test_recusa_sentido_invalido(usuario, linha, sentido):
    with pytest.raises(RelatoInvalido) as erro:
        registrar_relato(usuario, linha, sentido, Lotacao.VAZIO)

    assert "sentido" in erro.value.args[0]
    assert not Relato.objects.exists()


def test_recusa_relato_sem_linha(usuario):
    with pytest.raises(RelatoInvalido) as erro:
        registrar_relato(usuario, None, Sentido.IDA, Lotacao.VAZIO)

    assert "linha" in erro.value.args[0]
    assert not Relato.objects.exists()
