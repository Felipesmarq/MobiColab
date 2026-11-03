"""RD03 — camada ouro (issue #32)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from dados.mock.config import carregar_config
from dados.mock.gerador import gerar
from dados.pipeline import banco, bronze, ouro, prata
from dados.pipeline.esquemas import (
    OURO_QUALIDADE_DIARIA,
    OURO_RELATOS_POR_HORA,
    OURO_TAXAS_POR_LINHA,
    PRATA_RELATOS,
    TABELAS_OURO,
)
from relatos.models import ArCondicionado, ConfortoTermico, Lotacao, Relato, VagaPcd
from transporte.models import Linha, Sentido

pytestmark = pytest.mark.django_db

UTC = ZoneInfo("UTC")
NOVE_E_MEIA = datetime(2026, 10, 1, 9, 30, tzinfo=UTC)  # 06:30 em Recife


@pytest.fixture
def externos(tmp_path):
    (tmp_path / "temperatura").mkdir()
    return tmp_path


@pytest.fixture
def linhas():
    call_command("loaddata", "linhas_dev", verbosity=0)


@pytest.fixture
def mock(linhas, externos):
    config = carregar_config()
    config.valores["periodo.dias"] = 2
    config.valores["usuarios.quantidade"] = 30
    gerar(config, fim=date(2026, 10, 1), pasta_temperatura=externos / "temperatura")


def _pipeline(externos):
    bronze.executar(externos, agora=timezone.now())
    prata.executar()
    return ouro.executar()


def _relato(n=0, **campos):
    usuario, _ = get_user_model().objects.get_or_create(email=f"autor{n}@exemplo.com")
    padrao = {
        "usuario": usuario,
        "linha": Linha.objects.get(codigo="061"),
        "sentido": Sentido.IDA,
        "lotacao": Lotacao.LOTADO,
        "criado_em": NOVE_E_MEIA,
    }
    return Relato.objects.create(**{**padrao, **campos})


def test_soma_das_contagens_bate_com_a_prata(mock, externos):
    _pipeline(externos)
    por_hora = banco.ler(OURO_RELATOS_POR_HORA)
    assert por_hora["n_relatos"].sum() == len(banco.ler(PRATA_RELATOS))
    lotacao = por_hora[["n_vazio", "n_moderado", "n_lotado"]].sum(axis=1)
    assert (lotacao == por_hora["n_relatos"]).all()
    ar = por_hora[["n_ar_funcionando", "n_ar_nao_funcionando", "n_sem_ar", "n_ar_nao_informado"]]
    assert (ar.sum(axis=1) == por_hora["n_relatos"]).all()


def test_ouro_so_tem_agregados(mock, externos):
    """Dado o dashboard, então ele exibe só agregados — nenhum identificador individual."""
    _pipeline(externos)
    for tabela in TABELAS_OURO:
        colunas = set(banco.ler(tabela).columns)
        assert not {"id", "usuario_id", "relato_id", "prefixo_veiculo"} & colunas, tabela.nome


def test_contagens_por_dimensao(linhas, externos):
    _relato(1, ar_condicionado=ArCondicionado.NAO_FUNCIONANDO, conforto_termico="quente")
    _relato(2, lotacao=Lotacao.VAZIO, vaga_pcd=VagaPcd.OCUPADA)
    _relato(3, lotacao=Lotacao.MODERADO, ar_condicionado=ArCondicionado.SEM_AR)
    _pipeline(externos)

    linha = banco.ler(OURO_RELATOS_POR_HORA).iloc[0]
    assert (linha["data"], linha["hora"], linha["linha_codigo"]) == (date(2026, 10, 1), 6, "061")
    assert (linha["n_relatos"], linha["n_lotado"], linha["n_vazio"], linha["n_moderado"]) == (
        3,
        1,
        1,
        1,
    )
    assert (linha["n_ar_nao_funcionando"], linha["n_sem_ar"], linha["n_ar_nao_informado"]) == (
        1,
        1,
        1,
    )
    assert (linha["n_quente"], linha["n_conforto_nao_informado"]) == (1, 2)
    assert (linha["n_vaga_ocupada"], linha["n_vaga_nao_informada"]) == (1, 2)
    assert linha["faixa_horaria"] == "pico_manha"
    assert linha["destino"] == "Piedade"


def test_temperatura_da_hora_entra_no_agregado(linhas, externos):
    (externos / "temperatura" / "inmet.csv").write_text(
        "data_hora,temperatura_c,fonte\n2026-10-01T09:00:00+00:00,31.5,inmet\n", encoding="utf-8"
    )
    _relato()
    _relato(2, criado_em=NOVE_E_MEIA + timedelta(hours=3))
    _pipeline(externos)
    por_hora = banco.ler(OURO_RELATOS_POR_HORA).set_index("hora")
    assert por_hora.loc[6, "temperatura_c"] == 31.5
    assert por_hora.loc[6, "temperatura_fonte"] == "inmet"
    assert pd.isna(por_hora.loc[9, "temperatura_c"])
    assert por_hora.loc[9, "temperatura_fonte"] == "ausente"


def test_taxas_com_numerador_e_denominador(linhas, externos):
    _relato(1, ar_condicionado=ArCondicionado.NAO_FUNCIONANDO, conforto_termico="quente")
    _relato(2, ar_condicionado=ArCondicionado.FUNCIONANDO, conforto_termico="agradavel")
    _relato(3, lotacao=Lotacao.VAZIO, ar_condicionado=ArCondicionado.SEM_AR)
    _relato(4, lotacao=Lotacao.VAZIO)
    _pipeline(externos)

    taxa = banco.ler(OURO_TAXAS_POR_LINHA).iloc[0]
    assert (taxa["n_lotado"], taxa["n_relatos"], taxa["taxa_lotado"]) == (2, 4, 0.5)
    # "sem ar" não entra no denominador da falha: só veículos climatizados informados.
    assert taxa["n_ar_climatizado_informado"] == 2
    assert taxa["taxa_ar_nao_funcionando"] == 0.5
    assert taxa["taxa_quente"] == 0.5
    assert pd.isna(taxa["taxa_vaga_ocupada"])  # ninguém informou: vazio, não zero


def test_qualidade_diaria(linhas, externos):
    _relato(1, removido_em=NOVE_E_MEIA + timedelta(minutes=5), motivo_remocao="x")
    antigo = _relato(2, lotacao=Lotacao.VAZIO)
    novo = _relato(2, criado_em=NOVE_E_MEIA + timedelta(minutes=3))
    antigo.substituido_por = novo
    antigo.save()
    _pipeline(externos)

    dia = banco.ler(OURO_QUALIDADE_DIARIA).iloc[0]
    assert dia["data"] == date(2026, 10, 1)
    assert (dia["n_relatos_total"], dia["n_validos"]) == (3, 1)
    assert (dia["n_removidos"], dia["n_substituidos"]) == (1, 1)
    assert dia["n_usuarios_ativos"] == 2
    assert dia["n_linhas_com_relato"] == 1


def test_taxa_com_denominador_zero_fica_vazia():
    resultado = ouro.taxa(pd.Series([0, 1]), pd.Series([0, 2]))
    assert pd.isna(resultado.iloc[0])
    assert resultado.iloc[1] == 0.5


def test_comando_pipeline_gera_a_ouro(mock, externos, monkeypatch, capsys):
    monkeypatch.setattr(bronze, "PASTA_EXTERNOS", externos)
    call_command("pipeline")
    saida = capsys.readouterr().out
    assert "ouro.relatos_por_hora" in saida
    assert len(banco.ler(OURO_RELATOS_POR_HORA)) > 0


def test_ouro_vazia_quando_nao_ha_relatos(linhas, externos):
    resumo = _pipeline(externos)
    assert resumo == {"relatos_por_hora": 0, "taxas_por_linha": 0, "qualidade_diaria": 0}


def test_conforto_quente_usa_o_valor_da_rn01():
    assert ouro.INDICADORES["n_quente"] == ("conforto_termico", ConfortoTermico.QUENTE)
