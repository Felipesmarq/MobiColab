"""RN05 — substituição de relato dentro de RELATO_INTERVALO_MIN (issue #13, ADR 0013)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from relatos.models import Confirmacao, Lotacao, Relato
from relatos.regras import UsuarioBloqueado, registrar_relato
from transporte.models import Linha, Modal, Sentido

pytestmark = pytest.mark.django_db

Usuario = get_user_model()


@pytest.fixture(autouse=True)
def intervalo_da_spec(settings):
    settings.RELATO_INTERVALO_MIN = 10


@pytest.fixture
def agora(monkeypatch):
    """Congela o relógio do servidor para testar as bordas da janela."""
    instante = timezone.now()
    monkeypatch.setattr(timezone, "now", lambda: instante)
    return instante


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
def relato_antigo(agora, usuario, linha):
    """Cria um relato do usuário feito `minutos` antes de `agora`."""

    def criar(minutos, **campos):
        valores = {
            "usuario": usuario,
            "linha": linha,
            "sentido": Sentido.IDA,
            "lotacao": Lotacao.VAZIO,
            "criado_em": agora - timedelta(minutes=minutos),
        }
        return Relato.objects.create(**{**valores, **campos})

    return criar


def test_relato_novo_dentro_da_janela_substitui_o_anterior(agora, usuario, linha, relato_antigo):
    anterior = relato_antigo(minutos=9)

    novo = registrar_relato(usuario, linha, Sentido.IDA, Lotacao.LOTADO)

    anterior.refresh_from_db()
    assert anterior.substituido_por == novo
    assert list(novo.substituiu.all()) == [anterior]
    assert Relato.objects.count() == 2


def test_fora_da_janela_os_dois_relatos_seguem_ativos(agora, usuario, linha, relato_antigo):
    anterior = relato_antigo(minutos=11)

    registrar_relato(usuario, linha, Sentido.IDA, Lotacao.LOTADO)

    anterior.refresh_from_db()
    assert anterior.substituido_por is None


def test_com_exatamente_o_intervalo_nao_substitui(agora, usuario, linha, relato_antigo):
    """ "Menos de" RELATO_INTERVALO_MIN: a borda de 10 min já está fora."""
    anterior = relato_antigo(minutos=10)

    registrar_relato(usuario, linha, Sentido.IDA, Lotacao.LOTADO)

    anterior.refresh_from_db()
    assert anterior.substituido_por is None


def test_nao_substitui_relato_de_outro_usuario(agora, usuario, linha, relato_antigo):
    outra = Usuario.objects.create_user(email="outra@exemplo.com", password="senha-forte-123")
    do_outro = relato_antigo(minutos=2, usuario=outra)

    registrar_relato(usuario, linha, Sentido.IDA, Lotacao.LOTADO)

    do_outro.refresh_from_db()
    assert do_outro.substituido_por is None


def test_nao_substitui_relato_de_outro_sentido(agora, usuario, linha, relato_antigo):
    na_volta = relato_antigo(minutos=2, sentido=Sentido.VOLTA)

    registrar_relato(usuario, linha, Sentido.IDA, Lotacao.LOTADO)

    na_volta.refresh_from_db()
    assert na_volta.substituido_por is None


def test_nao_substitui_relato_de_outra_linha(agora, usuario, linha, relato_antigo):
    outra_linha = Linha.objects.create(
        codigo="061", nome="Outra", modal=Modal.ONIBUS, destino_ida="Boa Viagem"
    )
    de_outra_linha = relato_antigo(minutos=2, linha=outra_linha)

    registrar_relato(usuario, linha, Sentido.IDA, Lotacao.LOTADO)

    de_outra_linha.refresh_from_db()
    assert de_outra_linha.substituido_por is None


def test_confirmacoes_do_anterior_ficam_com_ele(agora, usuario, linha, relato_antigo):
    anterior = relato_antigo(minutos=2)
    votante = Usuario.objects.create_user(email="votante@exemplo.com", password="senha-forte-123")
    Confirmacao.objects.create(relato=anterior, usuario=votante, ainda_vale=True)

    novo = registrar_relato(usuario, linha, Sentido.IDA, Lotacao.LOTADO)

    assert anterior.confirmacoes.count() == 1
    assert novo.confirmacoes.count() == 0


def test_nao_substitui_relato_removido_pela_moderacao(agora, usuario, linha, relato_antigo):
    removido = relato_antigo(minutos=2, removido_em=agora, motivo_remocao="spam")

    registrar_relato(usuario, linha, Sentido.IDA, Lotacao.LOTADO)

    removido.refresh_from_db()
    assert removido.substituido_por is None


def test_nao_troca_o_substituto_de_relato_ja_substituido(agora, usuario, linha, relato_antigo):
    """A -> B já substituído; um novo C substitui só B, e A continua apontando para B."""
    a = relato_antigo(minutos=8)
    b = relato_antigo(minutos=5)
    a.substituido_por = b
    a.save()

    c = registrar_relato(usuario, linha, Sentido.IDA, Lotacao.LOTADO)

    a.refresh_from_db()
    b.refresh_from_db()
    assert a.substituido_por == b
    assert b.substituido_por == c


def test_bloqueio_feito_depois_de_carregar_o_usuario_e_respeitado(agora, usuario, linha):
    """A moderação bloqueou no banco; a instância em memória (sessão) ainda diz ativo."""
    Usuario.objects.filter(pk=usuario.pk).update(is_active=False)
    assert usuario.is_active  # instância velha

    with pytest.raises(UsuarioBloqueado):
        registrar_relato(usuario, linha, Sentido.IDA, Lotacao.LOTADO)

    assert not Relato.objects.exists()
