"""RN02 — peso do relato com decaimento exponencial (issue #17)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from relatos.models import Confirmacao, Lotacao, Relato
from relatos.regras import peso_do_relato
from transporte.models import Linha, Modal, Sentido

pytestmark = pytest.mark.django_db

Usuario = get_user_model()


@pytest.fixture(autouse=True)
def parametros_da_spec(settings):
    """Valores da spec, para o teste não depender do ambiente."""
    settings.RELATO_MEIA_VIDA_MIN = 15
    settings.RELATO_PESO_CONFIRMACAO = 0.5
    settings.RELATO_PESO_CONTESTACAO = 0.5


@pytest.fixture
def agora():
    return timezone.now()


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
def relato_de(linha, agora):
    """Cria um relato feito `minutos` antes de `agora`."""
    autor = Usuario.objects.create_user(email="autora@exemplo.com", password="senha-forte-123")

    def criar(minutos):
        return Relato.objects.create(
            usuario=autor,
            linha=linha,
            sentido=Sentido.IDA,
            lotacao=Lotacao.MODERADO,
            criado_em=agora - timedelta(minutes=minutos),
        )

    return criar


@pytest.fixture
def votar(agora):
    """Registra `quantos` votos de outros passageiros, `minutos` antes de `agora`."""

    def registrar(relato, *, ainda_vale, quantos=1, minutos=0):
        for _ in range(quantos):
            votante = Usuario.objects.create_user(
                email=f"votante{Usuario.objects.count()}@exemplo.com", password="senha-forte-123"
            )
            Confirmacao.objects.create(
                relato=relato,
                usuario=votante,
                ainda_vale=ainda_vale,
                criado_em=agora - timedelta(minutes=minutos),
            )

    return registrar


@pytest.mark.parametrize(
    ("confirmacoes", "contestacoes", "peso_esperado"),
    [(1, 0, 1.5), (0, 1, 0.5), (1, 1, 1.0)],
)
def test_confirmacao_soma_e_contestacao_subtrai(
    relato_de, votar, agora, confirmacoes, contestacoes, peso_esperado
):
    relato = relato_de(0)
    votar(relato, ainda_vale=True, quantos=confirmacoes)
    votar(relato, ainda_vale=False, quantos=contestacoes)

    assert peso_do_relato(relato, agora) == pytest.approx(peso_esperado)


def test_relato_com_data_no_futuro_nao_pesa_mais_que_um(relato_de, agora):
    """Diferença de relógio: `agora` anterior ao relato não pode inflar o peso acima de 1."""
    relato = relato_de(-10)

    assert peso_do_relato(relato, agora) == pytest.approx(1.0)


@pytest.mark.parametrize("contestacoes", [2, 3])
def test_peso_nunca_fica_negativo(relato_de, votar, agora, contestacoes):
    """2 contestações zeram o fator (1 - 0,5·2); 3 o deixariam negativo."""
    relato = relato_de(0)
    votar(relato, ainda_vale=False, quantos=contestacoes)

    assert peso_do_relato(relato, agora) == 0.0


def test_confirmacao_renova_o_tempo_do_relato(relato_de, votar, agora):
    """Relato de 30 min, confirmado agora: o t recomeça (1 · 1,5 = 1,5, não 0,25 · 1,5)."""
    relato = relato_de(30)
    votar(relato, ainda_vale=True, minutos=0)

    assert peso_do_relato(relato, agora) == pytest.approx(1.5)


def test_t_conta_desde_a_confirmacao_mais_recente(relato_de, votar, agora):
    """Confirmações aos 20 e 10 min atrás: vale a de 10 min (peso 0,5^(10/15) · 2)."""
    relato = relato_de(30)
    votar(relato, ainda_vale=True, minutos=20)
    votar(relato, ainda_vale=True, minutos=10)

    assert peso_do_relato(relato, agora) == pytest.approx(2 * 0.5 ** (10 / 15))


def test_contestacao_nao_renova_o_tempo_do_relato(relato_de, votar, agora):
    """Relato de 30 min, contestado agora: t segue em 30 (0,25 · (1 - 0,5) = 0,125)."""
    relato = relato_de(30)
    votar(relato, ainda_vale=False, minutos=0)

    assert peso_do_relato(relato, agora) == pytest.approx(0.125)


@pytest.mark.parametrize(
    ("minutos", "peso_esperado"),
    [(0, 1.0), (15, 0.5), (30, 0.25)],
)
def test_relato_sem_votos_perde_metade_a_cada_meia_vida(relato_de, agora, minutos, peso_esperado):
    relato = relato_de(minutos)

    assert peso_do_relato(relato, agora) == pytest.approx(peso_esperado)
