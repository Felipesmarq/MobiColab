"""RD03 — comando pipeline e camada bronze (issue #30)."""

from datetime import date, timedelta

import pandas as pd
import pytest
from django.core.management import call_command
from django.utils import timezone

from dados.mock.config import carregar_config
from dados.mock.gerador import gerar, limpar_mock
from dados.pipeline import banco, bronze
from dados.pipeline.esquemas import (
    BRONZE_EXECUCOES,
    BRONZE_LINHAS,
    BRONZE_RELATOS,
    BRONZE_TEMPERATURA,
)
from relatos.models import Relato

pytestmark = pytest.mark.django_db


@pytest.fixture
def externos(tmp_path):
    (tmp_path / "temperatura").mkdir()
    return tmp_path


@pytest.fixture
def mock(externos):
    call_command("loaddata", "linhas_dev", verbosity=0)
    config = carregar_config()
    config.valores["periodo.dias"] = 2
    config.valores["usuarios.quantidade"] = 30
    gerar(config, fim=date(2026, 10, 1), pasta_temperatura=externos / "temperatura")
    return config


def _rodar(externos, minutos=0):
    return bronze.executar(externos, agora=timezone.now() + timedelta(minutes=minutos))


def test_primeira_execucao_copia_tudo(mock, externos):
    resumo = _rodar(externos)
    assert resumo["relatos"] == (Relato.objects.count(), Relato.objects.count())
    assert resumo["linhas"] == (5, 5)
    assert resumo["temperatura"] == (48, 48)
    assert len(banco.ler(BRONZE_RELATOS)) == Relato.objects.count()


def test_execucao_sem_mudancas_nao_acrescenta_nada(mock, externos):
    _rodar(externos)
    resumo = _rodar(externos, minutos=1)
    assert all(novas == 0 for _, novas in resumo.values())
    assert len(banco.ler(BRONZE_RELATOS)) == Relato.objects.count()


def test_mudanca_na_origem_vira_versao_nova_sem_editar_a_antiga(mock, externos):
    _rodar(externos)
    relato = Relato.objects.filter(removido_em__isnull=True).first()
    relato.removido_em = timezone.now()
    relato.motivo_remocao = "teste"
    relato.save()

    resumo = _rodar(externos, minutos=1)
    assert resumo["relatos"][1] == 1

    versoes = banco.ler(BRONZE_RELATOS)
    deste = versoes[versoes["id"] == relato.pk].sort_values("_extraido_em")
    assert len(deste) == 2
    assert pd.isna(deste.iloc[0]["removido_em"])
    assert deste.iloc[1]["motivo_remocao"] == "teste"
    assert deste.iloc[0]["_hash"] != deste.iloc[1]["_hash"]


def test_linha_que_some_da_origem_e_marcada_como_apagada(mock, externos):
    _rodar(externos)
    total = Relato.objects.count()
    limpar_mock()
    resumo = _rodar(externos, minutos=1)
    assert resumo["relatos"] == (0, total)

    atuais = bronze.versoes_atuais(banco.ler(BRONZE_RELATOS), BRONZE_RELATOS)
    assert atuais["_apagado_na_origem"].all()
    assert len(banco.ler(BRONZE_RELATOS)) == 2 * total

    # Nada mais a marcar numa terceira execução.
    assert _rodar(externos, minutos=2)["relatos"] == (0, 0)


def test_relato_e_rotulado_como_mock_ou_real(mock, externos):
    _rodar(externos)
    assert set(banco.ler(BRONZE_RELATOS)["origem"]) == {"mock"}


def test_bronze_nao_guarda_dados_pessoais(mock, externos):
    _rodar(externos)
    colunas = set(banco.ler(BRONZE_RELATOS).columns)
    assert not {"email", "usuario__email", "first_name", "last_name"} & colunas


def test_temperatura_de_arquivo_externo(mock, externos):
    (externos / "temperatura" / "inmet.csv").write_text(
        "data_hora,temperatura_c,fonte\n2026-10-01T10:00:00-03:00,29.5,inmet\n", encoding="utf-8"
    )
    _rodar(externos)
    temperatura = banco.ler(BRONZE_TEMPERATURA)
    inmet = temperatura[temperatura["fonte"] == "inmet"]
    assert len(inmet) == 1
    assert inmet.iloc[0]["temperatura_c"] == 29.5
    assert inmet.iloc[0]["arquivo"] == "inmet.csv"


def test_arquivo_de_temperatura_sem_colunas_e_recusado(mock, externos):
    (externos / "temperatura" / "ruim.csv").write_text("hora,valor\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ruim.csv"):
        _rodar(externos)


def test_cada_execucao_fica_registrada(mock, externos):
    _rodar(externos)
    _rodar(externos, minutos=1)
    execucoes = banco.ler(BRONZE_EXECUCOES)
    assert len(execucoes) == 2 * 6
    assert execucoes["extraido_em"].nunique() == 2


def test_tabela_tem_nome_por_backend():
    nome = banco.nome_tabela(BRONZE_LINHAS)
    assert nome in ('"bronze"."linhas"', '"bronze__linhas"')


def test_comando_pipeline(mock, externos, monkeypatch, capsys):
    monkeypatch.setattr(bronze, "PASTA_EXTERNOS", externos)
    call_command("pipeline")
    saida = capsys.readouterr().out
    assert "bronze.relatos" in saida
    assert "Pipeline concluído" in saida
