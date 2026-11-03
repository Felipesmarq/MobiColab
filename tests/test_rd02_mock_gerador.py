"""RD02 — gerador de dados mockados (issue #28)."""

import csv
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from dados.mock.config import carregar_config
from dados.mock.gerador import DOMINIO_MOCK, GeracaoInvalida, eh_mock, gerar, limpar_mock
from relatos.models import Confirmacao, Lotacao, Relato

pytestmark = pytest.mark.django_db

FIM = date(2026, 10, 1)


@pytest.fixture
def linhas():
    call_command("loaddata", "linhas_dev", verbosity=0)


@pytest.fixture
def config():
    config = carregar_config()
    config.valores["periodo.dias"] = 3
    config.valores["usuarios.quantidade"] = 40
    return config


def _assinatura():
    return list(
        Relato.objects.order_by("criado_em", "linha_id", "sentido", "lotacao").values_list(
            "linha__codigo", "sentido", "criado_em", "lotacao", "ar_condicionado", "vaga_pcd"
        )
    )


def test_gera_relatos_confirmacoes_e_temperatura(linhas, config, tmp_path):
    resultado = gerar(config, fim=FIM, pasta_temperatura=tmp_path)

    assert resultado.usuarios == 40
    assert resultado.relatos == Relato.objects.count() > 0
    assert resultado.confirmacoes + resultado.contestacoes == Confirmacao.objects.count() > 0

    with open(resultado.arquivo_temperatura, encoding="utf-8") as arquivo:
        linhas_csv = list(csv.DictReader(arquivo))
    assert len(linhas_csv) == 3 * 24
    assert {linha["fonte"] for linha in linhas_csv} == {"mock"}


def test_toda_saida_e_marcada_como_mock(linhas, config, tmp_path):
    gerar(config, fim=FIM, pasta_temperatura=tmp_path)
    emails = Relato.objects.values_list("usuario__email", flat=True).distinct()
    assert emails and all(eh_mock(email) for email in emails)


def test_mesma_semente_gera_os_mesmos_dados(linhas, config, tmp_path):
    gerar(config, fim=FIM, pasta_temperatura=tmp_path)
    primeira = _assinatura()
    limpar_mock()
    gerar(config, fim=FIM, pasta_temperatura=tmp_path)
    assert _assinatura() == primeira


def test_periodo_termina_no_dia_pedido(linhas, config, tmp_path):
    gerar(config, fim=FIM, pasta_temperatura=tmp_path)
    datas = {_local(r).date() for r in Relato.objects.all()}
    assert min(datas) == FIM - timedelta(days=2)
    assert max(datas) == FIM


def test_substituicao_segue_a_rn05(linhas, config, tmp_path):
    config.valores["interacoes.prob_substituicao"] = 0.5
    gerar(config, fim=FIM, pasta_temperatura=tmp_path)
    substituidos = Relato.objects.filter(substituido_por__isnull=False).select_related(
        "substituido_por"
    )
    assert substituidos.exists()
    limite = timedelta(minutes=settings.RELATO_INTERVALO_MIN)
    for antigo in substituidos:
        novo = antigo.substituido_por
        assert (novo.usuario_id, novo.linha_id, novo.sentido) == (
            antigo.usuario_id,
            antigo.linha_id,
            antigo.sentido,
        )
        assert timedelta(0) < novo.criado_em - antigo.criado_em < limite


def test_votos_seguem_a_rn06(linhas, config, tmp_path):
    config.valores["interacoes.confirmacoes_por_relato"] = 2.0
    gerar(config, fim=FIM, pasta_temperatura=tmp_path)
    votos = Confirmacao.objects.select_related("relato")
    assert votos.exists()
    assert not any(v.usuario_id == v.relato.usuario_id for v in votos)
    assert not votos.filter(relato__substituido_por__isnull=False).exists()
    assert not votos.filter(relato__removido_em__isnull=False).exists()


def test_remocoes_tem_motivo(linhas, config, tmp_path):
    config.valores["interacoes.prob_remocao_comum"] = 0.2
    gerar(config, fim=FIM, pasta_temperatura=tmp_path)
    removidos = Relato.objects.filter(removido_em__isnull=False)
    assert removidos.exists()
    assert all(r.motivo_remocao and r.removido_em >= r.criado_em for r in removidos)


def test_padroes_programados_aparecem(linhas, config, tmp_path):
    """H1 embutida: 'lotado' é mais frequente no pico que fora dele."""
    config.valores["periodo.dias"] = 7
    config.valores["usuarios.fracao_trolls"] = 0
    gerar(config, fim=FIM, pasta_temperatura=tmp_path)
    pico = set(config["lotacao.horas_pico"])

    def taxa_lotado(no_pico):
        relatos = [r for r in Relato.objects.all() if (_local(r).hour in pico) == no_pico]
        return sum(r.lotacao == Lotacao.LOTADO for r in relatos) / len(relatos)

    assert taxa_lotado(True) > taxa_lotado(False) + 0.2


def _local(relato):
    return relato.criado_em.astimezone(ZoneInfo(settings.TIME_ZONE))


def test_recusa_gerar_sem_linhas(config, tmp_path):
    with pytest.raises(GeracaoInvalida, match="loaddata"):
        gerar(config, fim=FIM, pasta_temperatura=tmp_path)


def test_recusa_gerar_por_cima_de_mock_existente(linhas, config, tmp_path):
    gerar(config, fim=FIM, pasta_temperatura=tmp_path)
    with pytest.raises(GeracaoInvalida, match="--limpar"):
        gerar(config, fim=FIM, pasta_temperatura=tmp_path)


def test_limpar_nao_toca_em_dados_reais(linhas, config, tmp_path):
    real = get_user_model().objects.create_user(email="real@exemplo.com")
    gerar(config, fim=FIM, pasta_temperatura=tmp_path)
    limpar_mock()
    assert list(get_user_model().objects.all()) == [real]
    assert not Relato.objects.exists()


def test_comando_gerar_mock(linhas, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("dados.mock.gerador.PASTA_TEMPERATURA", tmp_path)
    call_command("gerar_mock", "--dias", "1", "--fim", "2026-10-01")
    saida = capsys.readouterr().out
    assert "DADOS MOCKADOS" in saida
    assert get_user_model().objects.filter(email__endswith="@" + DOMINIO_MOCK).exists()
    with pytest.raises(CommandError, match="--limpar"):
        call_command("gerar_mock", "--dias", "1", "--fim", "2026-10-01")
    call_command("gerar_mock", "--dias", "1", "--fim", "2026-10-01", "--limpar")
