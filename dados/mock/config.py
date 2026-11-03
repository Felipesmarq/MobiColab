"""Leitura e validação do `config.yaml` do gerador de dados mockados (RD02).

Todo parâmetro do arquivo é um par `{valor, fonte}`. A validação recusa
parâmetro sem fonte e valores impossíveis (probabilidade fora de [0, 1],
distribuição que não soma 1 etc.), para o gerador nunca rodar com uma
configuração quebrada.
"""

from dataclasses import dataclass, field
from math import isclose
from pathlib import Path

import yaml

CAMINHO_PADRAO = Path(__file__).with_name("config.yaml")

NIVEIS_LOTACAO = ("vazio", "moderado", "lotado")

PROBABILIDADES = [
    "usuarios.fracao_trolls",
    "climatizacao.fracao_frota_com_ar",
    "climatizacao.prob_ar_nao_funcionando",
    "preenchimento.conforto_termico",
    "preenchimento.vaga_pcd",
    "preenchimento.ar_quando_funcionando",
    "preenchimento.ar_quando_nao_funcionando",
    "preenchimento.ar_quando_sem_ar",
    "preenchimento.prefixo_veiculo",
    "interacoes.prob_substituicao",
    "interacoes.prob_ainda_vale",
    "interacoes.prob_ainda_vale_troll",
    "interacoes.prob_remocao_troll",
    "interacoes.prob_remocao_comum",
    "lotacao.acrescimo_lotado_terminal",
]

INTEIROS_POSITIVOS = [
    "reprodutibilidade.semente",
    "periodo.dias",
    "usuarios.quantidade",
    "volume.relatos_por_hora_pico",
]

DISTRIBUICOES_LOTACAO = ["lotacao.pico", "lotacao.fora_do_pico", "lotacao.madrugada"]


class ConfigInvalida(ValueError):
    def __init__(self, erros):
        self.erros = erros
        super().__init__("config.yaml inválido:\n- " + "\n- ".join(erros))


@dataclass
class ConfigMock:
    """Valores e fontes de cada parâmetro, indexados por "secao.parametro"."""

    valores: dict = field(default_factory=dict)
    fontes: dict = field(default_factory=dict)

    def __getitem__(self, caminho):
        return self.valores[caminho]


def carregar_config(caminho=CAMINHO_PADRAO):
    with open(caminho, encoding="utf-8") as arquivo:
        bruto = yaml.safe_load(arquivo) or {}
    config = _achatar(bruto)
    validar(config)
    return config


def _achatar(bruto):
    """Transforma {secao: {param: {valor, fonte}}} em ConfigMock; erros de formato acumulam."""
    erros = []
    config = ConfigMock()
    for secao, parametros in bruto.items():
        if not isinstance(parametros, dict):
            erros.append(f"{secao}: a seção precisa ser um mapa de parâmetros")
            continue
        for nome, item in parametros.items():
            caminho = f"{secao}.{nome}"
            if not isinstance(item, dict) or set(item) != {"valor", "fonte"}:
                erros.append(f"{caminho}: precisa ter exatamente as chaves 'valor' e 'fonte'")
                continue
            if not isinstance(item["fonte"], str) or not item["fonte"].strip():
                erros.append(f"{caminho}: a fonte não pode ficar vazia")
                continue
            config.valores[caminho] = item["valor"]
            config.fontes[caminho] = item["fonte"].strip()
    if erros:
        raise ConfigInvalida(erros)
    return config


def validar(config):
    erros = []

    def checar(caminho, condicao, mensagem):
        if caminho not in config.valores:
            erros.append(f"{caminho}: parâmetro obrigatório ausente")
        elif not condicao(config.valores[caminho]):
            erros.append(f"{caminho}: {mensagem}")

    eh_numero = lambda v: isinstance(v, int | float) and not isinstance(v, bool)  # noqa: E731

    for caminho in PROBABILIDADES:
        checar(caminho, lambda v: eh_numero(v) and 0 <= v <= 1, "precisa estar entre 0 e 1")

    for caminho in INTEIROS_POSITIVOS:
        checar(caminho, lambda v: isinstance(v, int) and v > 0, "precisa ser inteiro positivo")

    for caminho in DISTRIBUICOES_LOTACAO:
        checar(
            caminho,
            lambda v: (
                isinstance(v, dict)
                and set(v) == set(NIVEIS_LOTACAO)
                and all(eh_numero(p) and p >= 0 for p in v.values())
                and isclose(sum(v.values()), 1, abs_tol=1e-6)
            ),
            "precisa ter vazio, moderado e lotado somando 1",
        )

    checar(
        "volume.perfil_horario",
        lambda v: isinstance(v, list) and len(v) == 24 and all(eh_numero(p) and p >= 0 for p in v),
        "precisa ter 24 valores não negativos (0h a 23h)",
    )
    checar("volume.fator_fim_de_semana", lambda v: eh_numero(v) and v >= 0, "não pode ser negativo")

    for caminho in ("lotacao.horas_pico", "lotacao.horas_madrugada"):
        checar(
            caminho,
            lambda v: isinstance(v, list) and all(isinstance(h, int) and 0 <= h <= 23 for h in v),
            "precisa ser uma lista de horas entre 0 e 23",
        )

    checar(
        "climatizacao.fracao_frota_com_ar_por_linha",
        lambda v: isinstance(v, dict) and all(eh_numero(p) and 0 <= p <= 1 for p in v.values()),
        "precisa mapear código de linha para uma fração entre 0 e 1",
    )
    checar(
        "climatizacao.variacao_ar_entre_linhas", lambda v: eh_numero(v) and v >= 0, "não negativo"
    )

    for caminho in ("conforto_termico.sem_ar", "conforto_termico.ar_funcionando"):
        checar(
            caminho,
            lambda v: (
                isinstance(v, dict)
                and set(v) == {"prob_quente", "aumento_por_grau", "prob_frio"}
                and all(eh_numero(p) for p in v.values())
                and 0 <= v["prob_quente"] <= 1
                and 0 <= v["prob_frio"] <= 1
                and v["prob_quente"] + v["prob_frio"] <= 1
            ),
            "precisa ter prob_quente, aumento_por_grau e prob_frio, com quente + frio <= 1",
        )
    checar("conforto_termico.temperatura_referencia_c", eh_numero, "precisa ser número")

    for caminho in (
        "temperatura.media_diaria_c",
        "temperatura.amplitude_diaria_c",
        "temperatura.variacao_entre_dias_c",
        "temperatura.ruido_horario_c",
    ):
        checar(caminho, eh_numero, "precisa ser número")
    checar(
        "temperatura.hora_mais_quente",
        lambda v: isinstance(v, int) and 0 <= v <= 23,
        "precisa ser hora entre 0 e 23",
    )

    checar(
        "vaga_pcd.prob_ocupada_por_lotacao",
        lambda v: (
            isinstance(v, dict)
            and set(v) == set(NIVEIS_LOTACAO)
            and all(eh_numero(p) and 0 <= p <= 1 for p in v.values())
        ),
        "precisa ter vazio, moderado e lotado com probabilidades entre 0 e 1",
    )
    for caminho in ("usuarios.dispersao_atividade", "usuarios.atividade_troll"):
        checar(caminho, lambda v: eh_numero(v) and v >= 0, "não pode ser negativo")
    checar(
        "interacoes.confirmacoes_por_relato",
        lambda v: eh_numero(v) and v >= 0,
        "não pode ser negativo",
    )

    if erros:
        raise ConfigInvalida(erros)
