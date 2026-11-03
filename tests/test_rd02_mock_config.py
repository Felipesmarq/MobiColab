"""RD02 — parâmetros do gerador de dados mockados (issue #27)."""

import copy
import re

import pytest
import yaml

from dados.mock.config import CAMINHO_PADRAO, ConfigInvalida, _achatar, carregar_config, validar


@pytest.fixture
def bruto():
    with open(CAMINHO_PADRAO, encoding="utf-8") as arquivo:
        return yaml.safe_load(arquivo)


def test_config_do_repositorio_e_valida():
    config = carregar_config()
    assert config["periodo.dias"] > 0


def test_cada_parametro_tem_fonte_documentada(bruto):
    """Dado o gerador de mock, então cada parâmetro está documentado com a fonte."""
    config = carregar_config()
    total = sum(len(parametros) for parametros in bruto.values())
    assert len(config.fontes) == total
    assert all(fonte for fonte in config.fontes.values())


def test_frota_com_ar_vem_do_dado_real():
    config = carregar_config()
    assert config["climatizacao.fracao_frota_com_ar"] == pytest.approx(401 / 2462, abs=0.001)
    assert "401" in config.fontes["climatizacao.fracao_frota_com_ar"]


def test_parametro_sem_fonte_e_recusado(bruto):
    bruto["periodo"]["dias"] = {"valor": 28, "fonte": "  "}
    with pytest.raises(ConfigInvalida, match="periodo.dias"):
        _achatar(bruto)


def test_parametro_sem_par_valor_fonte_e_recusado(bruto):
    bruto["periodo"]["dias"] = 28
    with pytest.raises(ConfigInvalida, match="exatamente as chaves"):
        _achatar(bruto)


@pytest.mark.parametrize(
    ("caminho", "valor", "trecho"),
    [
        ("interacoes.prob_substituicao", 1.5, "entre 0 e 1"),
        ("lotacao.pico", {"vazio": 0.5, "moderado": 0.5, "lotado": 0.5}, "somando 1"),
        ("volume.perfil_horario", [1.0] * 23, "24 valores"),
        ("periodo.dias", 0, "inteiro positivo"),
        ("lotacao.horas_pico", [6, 24], "entre 0 e 23"),
        (
            "conforto_termico.sem_ar",
            {"prob_quente": 0.9, "aumento_por_grau": 0, "prob_frio": 0.2},
            "quente + frio",
        ),
    ],
)
def test_valores_impossiveis_sao_recusados(bruto, caminho, valor, trecho):
    config = _achatar(copy.deepcopy(bruto))
    config.valores[caminho] = valor
    with pytest.raises(ConfigInvalida, match=re.escape(trecho)):
        validar(config)


def test_parametro_obrigatorio_ausente_e_recusado(bruto):
    del bruto["climatizacao"]["prob_ar_nao_funcionando"]
    config = _achatar(bruto)
    with pytest.raises(ConfigInvalida, match="ausente"):
        validar(config)
