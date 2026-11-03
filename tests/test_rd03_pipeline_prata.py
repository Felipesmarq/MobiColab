"""RD03 — camada prata (issue #31)."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from dados.mock.config import carregar_config
from dados.mock.gerador import gerar, limpar_mock
from dados.pipeline import banco, bronze, prata
from dados.pipeline.esquemas import (
    BRONZE_RELATOS,
    PRATA_CONFIRMACOES,
    PRATA_LINHAS,
    PRATA_RELATOS,
    PRATA_RELATOS_HISTORICO,
    PRATA_TEMPERATURA,
)
from relatos.models import Confirmacao, Lotacao, Relato
from transporte.models import Linha, Sentido

pytestmark = pytest.mark.django_db

UTC = ZoneInfo("UTC")


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


def _pipeline(externos, minutos=0):
    bronze.executar(externos, agora=timezone.now() + timedelta(minutes=minutos))
    return prata.executar()


def _relato(**campos):
    usuario, _ = get_user_model().objects.get_or_create(email="autor@exemplo.com")
    padrao = {
        "usuario": usuario,
        "linha": Linha.objects.get(codigo="SUL"),
        "sentido": Sentido.IDA,
        "lotacao": Lotacao.LOTADO,
        "criado_em": datetime(2026, 10, 1, 9, 30, tzinfo=UTC),
    }
    return Relato.objects.create(**{**padrao, **campos})


def test_relatos_validos_excluem_removidos_e_substituidos(mock, externos):
    resumo = _pipeline(externos)
    esperado = Relato.objects.filter(removido_em__isnull=True, substituido_por__isnull=True)
    assert resumo["relatos"] == esperado.count()
    assert set(banco.ler(PRATA_RELATOS)["id"]) == set(esperado.values_list("id", flat=True))


def test_historico_guarda_todos_com_o_motivo(mock, externos):
    _pipeline(externos)
    historico = banco.ler(PRATA_RELATOS_HISTORICO)
    assert len(historico) == Relato.objects.count()
    removidos = set(Relato.objects.filter(removido_em__isnull=False).values_list("id", flat=True))
    assert set(historico[historico["removido"]]["id"]) == removidos
    assert not historico[historico["valido"]][["removido", "substituido"]].any().any()


def test_prata_e_reconstruida_so_a_partir_da_bronze(mock, externos):
    """Dado o comando executado do zero, a prata sai da bronze, sem ler o app."""
    primeira = _pipeline(externos)
    limpar_mock()  # a origem some, mas a bronze continua com as versões antigas
    banco.recriar(PRATA_RELATOS, banco.vazio(PRATA_RELATOS))
    assert prata.executar() == primeira


def test_apagados_na_origem_saem_da_prata(mock, externos):
    _pipeline(externos)
    limpar_mock()
    resumo = _pipeline(externos, minutos=1)
    assert resumo["relatos"] == 0
    assert resumo["relatos_historico"] == 0


def test_hora_local_e_faixa_horaria(linhas, externos):
    relato = _relato(criado_em=datetime(2026, 10, 1, 9, 30, tzinfo=UTC))  # 06:30 em Recife
    _pipeline(externos)
    linha = banco.ler(PRATA_RELATOS).set_index("id").loc[relato.pk]
    assert (linha["data"], linha["hora"], linha["faixa_horaria"]) == (
        date(2026, 10, 1),
        6,
        "pico_manha",
    )
    assert linha["dia_semana"] == 3  # quinta-feira
    assert not linha["fim_de_semana"]


def test_madrugada_vira_o_dia_anterior_no_fuso_local(linhas, externos):
    relato = _relato(criado_em=datetime(2026, 10, 2, 1, 0, tzinfo=UTC))  # 22h do dia 1 em Recife
    _pipeline(externos)
    linha = banco.ler(PRATA_RELATOS).set_index("id").loc[relato.pk]
    assert (linha["data"], linha["hora"], linha["faixa_horaria"]) == (
        date(2026, 10, 1),
        22,
        "noite",
    )


def test_opcional_vazio_vira_nao_informado(linhas, externos):
    relato = _relato(ar_condicionado="", conforto_termico="quente")
    _pipeline(externos)
    linha = banco.ler(PRATA_RELATOS).set_index("id").loc[relato.pk]
    assert linha["ar_condicionado"] == prata.NAO_INFORMADO
    assert linha["vaga_pcd"] == prata.NAO_INFORMADO
    assert linha["conforto_termico"] == "quente"


def test_valor_fora_da_rn01_fica_fora_da_analise(linhas, externos):
    relato = _relato()
    bronze.executar(externos)
    # Simula uma versão corrompida na bronze (o banco do app não deixaria gravar).
    versao = banco.ler(BRONZE_RELATOS)
    versao = versao[versao["id"] == relato.pk].assign(
        lotacao="cheio", _extraido_em=timezone.now() + timedelta(minutes=1), _hash="x"
    )
    banco.acrescentar(BRONZE_RELATOS, versao)
    prata.executar()

    historico = banco.ler(PRATA_RELATOS_HISTORICO).set_index("id")
    assert historico.loc[relato.pk, "fora_do_dominio"]
    assert relato.pk not in set(banco.ler(PRATA_RELATOS)["id"])


def test_dados_da_linha_e_destino(linhas, externos):
    ida = _relato(sentido=Sentido.IDA)
    volta = _relato(sentido=Sentido.VOLTA, linha=Linha.objects.get(codigo="061"))
    _pipeline(externos)
    relatos = banco.ler(PRATA_RELATOS).set_index("id")
    assert relatos.loc[ida.pk, "linha_codigo"] == "SUL"
    assert relatos.loc[ida.pk, "modal"] == "metro"
    assert relatos.loc[ida.pk, "destino"] == "Cajueiro Seco"
    assert relatos.loc[ida.pk, "passa_por_terminal"]  # TI Joana Bezerra
    assert relatos.loc[volta.pk, "destino"] == "Cais de Santa Rita"
    assert not relatos.loc[volta.pk, "passa_por_terminal"]
    assert relatos.loc[volta.pk, "operadora"] == prata.OPERADORA_NAO_INFORMADA


def test_linhas_sabem_se_passam_por_terminal(linhas, externos):
    _pipeline(externos)
    linhas_prata = banco.ler(PRATA_LINHAS).set_index("codigo")
    assert linhas_prata.loc["SUL", "passa_por_terminal_ida"]
    assert linhas_prata.loc["1076", "passa_por_terminal_volta"]  # TI Pelópidas
    assert not linhas_prata.loc["018", "passa_por_terminal_ida"]


def test_contagem_de_votos(linhas, externos):
    relato = _relato()
    for i, vale in enumerate([True, True, False]):
        votante = get_user_model().objects.create_user(email=f"v{i}@exemplo.com")
        Confirmacao.objects.create(relato=relato, usuario=votante, ainda_vale=vale)
    _pipeline(externos)
    linha = banco.ler(PRATA_RELATOS).set_index("id").loc[relato.pk]
    assert (linha["n_confirmacoes"], linha["n_contestacoes"]) == (2, 1)
    assert len(banco.ler(PRATA_CONFIRMACOES)) == 3


def _temperatura(externos, nome, linhas_csv):
    conteudo = "data_hora,temperatura_c,fonte\n" + "\n".join(linhas_csv) + "\n"
    (externos / "temperatura" / nome).write_text(conteudo, encoding="utf-8")


def test_temperatura_interpola_lacunas_curtas_e_deixa_as_longas(linhas, externos):
    horas = {0: 25.0, 3: 28.0, 4: 28.0, 9: 30.0}  # lacuna de 2 h (1–2) e de 4 h (5–8)
    _temperatura(
        externos,
        "inmet.csv",
        [f"2026-10-01T{h:02d}:00:00+00:00,{t},inmet" for h, t in horas.items()],
    )
    _pipeline(externos)
    serie = banco.ler(PRATA_TEMPERATURA).set_index("data_hora")
    hora = lambda h: pd.Timestamp(f"2026-10-01T{h:02d}:00:00", tz="UTC")  # noqa: E731

    assert len(serie) == 10
    assert serie.loc[hora(1), "temperatura_c"] == pytest.approx(26.0)
    assert serie.loc[hora(2), "temperatura_c"] == pytest.approx(27.0)
    assert serie.loc[hora(1), "fonte"] == "interpolada"
    assert serie.loc[hora(6), "fonte"] == "ausente"
    assert pd.isna(serie.loc[hora(6), "temperatura_c"])
    assert not serie.loc[hora(3), "interpolada"]
    assert serie.loc[hora(0), "hora"] == 21  # 21h do dia anterior em Recife


def test_temperatura_do_inmet_tem_prioridade_sobre_o_mock(linhas, externos):
    _temperatura(externos, "mock.csv", ["2026-10-01T10:00:00+00:00,20.0,mock"])
    _temperatura(externos, "inmet.csv", ["2026-10-01T10:00:00+00:00,29.0,inmet"])
    _pipeline(externos)
    serie = banco.ler(PRATA_TEMPERATURA)
    assert serie["temperatura_c"].tolist() == [29.0]
    assert serie["fonte"].tolist() == ["inmet"]


def test_executar_duas_vezes_da_o_mesmo_resultado(mock, externos):
    assert _pipeline(externos) == _pipeline(externos, minutos=1)


@pytest.mark.parametrize(
    ("hora", "faixa"),
    [(0, "madrugada"), (5, "inicio_manha"), (12, "entre_picos"), (18, "pico_tarde")],
)
def test_faixa_horaria(hora, faixa):
    assert prata.faixa_horaria(hora) == faixa


def test_faixa_horaria_recusa_hora_invalida():
    with pytest.raises(ValueError):
        prata.faixa_horaria(24)
