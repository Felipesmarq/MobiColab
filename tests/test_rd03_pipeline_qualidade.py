"""RD03 — testes de qualidade do pipeline (issue #33).

Cada teste roda o pipeline sobre o mock, corrompe uma camada de propósito e
confere que a regra certa pega o problema.
"""

from datetime import date

import pandas as pd
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from dados.mock.config import carregar_config
from dados.mock.gerador import gerar
from dados.pipeline import banco, bronze, ouro, prata, qualidade
from dados.pipeline.esquemas import (
    OURO_RELATOS_POR_HORA,
    OURO_TAXAS_POR_LINHA,
    PRATA_RELATOS,
    Coluna,
    Tabela,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def externos(tmp_path):
    (tmp_path / "temperatura").mkdir()
    return tmp_path


@pytest.fixture
def pipeline(externos):
    call_command("loaddata", "linhas_dev", verbosity=0)
    config = carregar_config()
    config.valores["periodo.dias"] = 2
    config.valores["usuarios.quantidade"] = 30
    gerar(config, fim=date(2026, 10, 1), pasta_temperatura=externos / "temperatura")
    bronze.executar(externos, agora=timezone.now())
    prata.executar()
    ouro.executar()


def _regras(falhas):
    return {falha.regra for falha in falhas}


def _corromper(tabela, alterar):
    df = banco.ler(tabela)
    banco.recriar(tabela, alterar(df))


def test_pipeline_sobre_o_mock_passa_em_tudo(pipeline):
    assert qualidade.verificar() == []


def test_relato_que_some_entre_camadas(pipeline):
    _corromper(PRATA_RELATOS, lambda df: df.iloc[1:])
    falhas = qualidade.verificar()
    assert "contagem" in _regras(falhas)
    assert any("prata.relatos" in falha.detalhe for falha in falhas)


def test_coluna_obrigatoria_vazia(pipeline):
    def sem_linha(df):
        df.loc[df.index[0], "linha_codigo"] = ""
        return df

    _corromper(PRATA_RELATOS, sem_linha)
    falhas = qualidade.verificar()
    assert any(f.regra == "nulo" and "linha_codigo" in f.detalhe for f in falhas)


def test_valor_fora_da_rn01(pipeline):
    def cheio(df):
        df.loc[df.index[0], "lotacao"] = "cheio"
        return df

    _corromper(PRATA_RELATOS, cheio)
    falhas = qualidade.verificar()
    assert any(f.regra == "dominio" and "cheio" in f.detalhe for f in falhas)


def test_taxa_fora_de_zero_a_um(pipeline):
    def taxa_impossivel(df):
        df.loc[df.index[0], "taxa_lotado"] = 1.5
        return df

    _corromper(OURO_TAXAS_POR_LINHA, taxa_impossivel)
    falhas = qualidade.verificar()
    assert any(f.regra == "dominio" and "taxa_lotado" in f.detalhe for f in falhas)


def test_chave_repetida_na_ouro(pipeline):
    _corromper(OURO_RELATOS_POR_HORA, lambda df: pd.concat([df, df.iloc[:1]]))
    assert {"unicidade", "contagem"} <= _regras(qualidade.verificar())


def test_identificador_na_ouro_e_recusado(monkeypatch):
    vazada = Tabela("ouro", "vazada", "", (Coluna("usuario_id", "inteiro", ""),))
    monkeypatch.setattr(qualidade, "TABELAS_OURO", (vazada,))
    falhas = qualidade._privacidade()
    assert [f.regra for f in falhas] == ["privacidade"]


def test_comando_falha_e_nao_grava_nada(externos, monkeypatch):
    call_command("loaddata", "linhas_dev", verbosity=0)
    monkeypatch.setattr(bronze, "PASTA_EXTERNOS", externos)
    monkeypatch.setattr(qualidade, "verificar", lambda: [qualidade.Falha("contagem", "simulada")])
    with pytest.raises(CommandError, match="simulada"):
        call_command("pipeline")
    assert not banco.existe(OURO_RELATOS_POR_HORA)


def test_comando_informa_que_a_qualidade_passou(pipeline, externos, monkeypatch, capsys):
    monkeypatch.setattr(bronze, "PASTA_EXTERNOS", externos)
    call_command("pipeline")
    assert "Testes de qualidade: tudo certo" in capsys.readouterr().out
