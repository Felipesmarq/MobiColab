"""Testes de qualidade do pipeline (RD03, issue #33).

Rodam ao fim de toda execução do `manage.py pipeline`. Se algum falhar, o
comando sai com erro e a transação inteira é desfeita: a ouro antiga continua
publicada e nada pela metade chega ao painel. No CI, uma execução de ponta a
ponta sobre o mock faz o build falhar se uma regra quebrar.

Três famílias de regra:

- contagens entre camadas (nada some nem aparece no caminho);
- nulos em colunas obrigatórias;
- domínios (RN01, faixas horárias, taxas entre 0 e 1) e unicidade das chaves.
"""

from dataclasses import dataclass

import pandas as pd

from relatos.models import ArCondicionado, ConfortoTermico, Lotacao, VagaPcd
from transporte.models import Modal, Sentido

from . import banco
from .esquemas import (
    BRONZE_RELATOS,
    OURO_QUALIDADE_DIARIA,
    OURO_RELATOS_POR_HORA,
    OURO_TAXAS_POR_LINHA,
    PRATA_CONFIRMACOES,
    PRATA_RELATOS,
    PRATA_RELATOS_HISTORICO,
    TABELAS_OURO,
)
from .prata import FAIXAS_HORARIAS, NAO_INFORMADO, atuais

COLUNAS_IDENTIFICADORAS = {"id", "usuario_id", "relato_id", "prefixo_veiculo", "email"}

OBRIGATORIAS_PRATA = (
    "id",
    "usuario_id",
    "linha_id",
    "sentido",
    "lotacao",
    "criado_em",
    "data",
    "hora",
    "faixa_horaria",
    "origem",
    "linha_codigo",
    "modal",
)

DOMINIOS_PRATA = {
    "lotacao": set(Lotacao.values),
    "sentido": set(Sentido.values),
    "conforto_termico": {*ConfortoTermico.values, NAO_INFORMADO},
    "ar_condicionado": {*ArCondicionado.values, NAO_INFORMADO},
    "vaga_pcd": {*VagaPcd.values, NAO_INFORMADO},
    "faixa_horaria": {nome for nome, _, _ in FAIXAS_HORARIAS},
    "origem": {"mock", "real"},
    "modal": set(Modal.values),
}

TAXAS = ("taxa_lotado", "taxa_ar_nao_funcionando", "taxa_quente", "taxa_vaga_ocupada")


@dataclass(frozen=True)
class Falha:
    regra: str
    detalhe: str

    def __str__(self):
        return f"[{self.regra}] {self.detalhe}"


def verificar():
    """Roda todas as regras e devolve a lista de falhas (vazia = tudo certo)."""
    bronze = atuais(banco.ler(BRONZE_RELATOS), BRONZE_RELATOS)
    historico = banco.ler(PRATA_RELATOS_HISTORICO)
    relatos = banco.ler(PRATA_RELATOS)
    confirmacoes = banco.ler(PRATA_CONFIRMACOES)
    por_hora = banco.ler(OURO_RELATOS_POR_HORA)
    taxas = banco.ler(OURO_TAXAS_POR_LINHA)
    qualidade = banco.ler(OURO_QUALIDADE_DIARIA)

    falhas = []
    falhas += _contagens(bronze, historico, relatos, confirmacoes, por_hora, taxas, qualidade)
    falhas += _nulos(relatos, por_hora)
    falhas += _dominios(relatos, taxas, por_hora)
    falhas += _unicidade(relatos, por_hora, taxas, qualidade)
    falhas += _privacidade()
    return falhas


def _igual(regra, descricao, esperado, obtido):
    if int(esperado) == int(obtido):
        return []
    return [Falha(regra, f"{descricao}: esperado {int(esperado)}, obtido {int(obtido)}")]


def _contagens(bronze, historico, relatos, confirmacoes, por_hora, taxas, qualidade):
    validos = int(historico["valido"].astype(bool).sum()) if len(historico) else 0
    votos_validos = confirmacoes["relato_id"].isin(relatos["id"]).sum()
    votos_contados = relatos["n_confirmacoes"].sum() + relatos["n_contestacoes"].sum()
    return [
        *_igual("contagem", "bronze → prata.relatos_historico", len(bronze), len(historico)),
        *_igual("contagem", "relatos_historico válidos → prata.relatos", validos, len(relatos)),
        *_igual(
            "contagem",
            "prata.relatos → soma de ouro.relatos_por_hora",
            len(relatos),
            por_hora["n_relatos"].sum(),
        ),
        *_igual(
            "contagem",
            "prata.relatos → soma de ouro.taxas_por_linha",
            len(relatos),
            taxas["n_relatos"].sum(),
        ),
        *_igual(
            "contagem",
            "relatos_historico → soma de ouro.qualidade_diaria (total)",
            len(historico),
            qualidade["n_relatos_total"].sum(),
        ),
        *_igual(
            "contagem",
            "prata.relatos → soma de ouro.qualidade_diaria (válidos)",
            len(relatos),
            qualidade["n_validos"].sum(),
        ),
        *_igual(
            "contagem",
            "votos em prata.confirmacoes → votos contados em prata.relatos",
            votos_validos,
            votos_contados,
        ),
    ]


def _nulos(relatos, por_hora):
    falhas = []
    for tabela, df, colunas in (
        (PRATA_RELATOS, relatos, OBRIGATORIAS_PRATA),
        (OURO_RELATOS_POR_HORA, por_hora, OURO_RELATOS_POR_HORA.chave),
    ):
        for coluna in colunas:
            serie = df[coluna]
            vazios = serie.isna() | (serie.astype(str) == "")
            if vazios.any():
                falhas.append(
                    Falha("nulo", f"{tabela.schema}.{tabela.nome}.{coluna}: {vazios.sum()} vazios")
                )
    return falhas


def _dominios(relatos, taxas, por_hora):
    falhas = []
    for coluna, valores in DOMINIOS_PRATA.items():
        fora = sorted(set(relatos[coluna].dropna()) - valores)
        if fora:
            falhas.append(Falha("dominio", f"prata.relatos.{coluna} fora do domínio: {fora}"))
    horas = pd.to_numeric(relatos["hora"], errors="coerce")
    if ((horas < 0) | (horas > 23)).any():
        falhas.append(Falha("dominio", "prata.relatos.hora fora de 0–23"))
    for coluna in TAXAS:
        serie = taxas[coluna].dropna()
        if ((serie < 0) | (serie > 1)).any():
            falhas.append(Falha("dominio", f"ouro.taxas_por_linha.{coluna} fora de [0, 1]"))
    contagens = [c for c in por_hora.columns if c.startswith("n_")]
    if len(por_hora) and (por_hora[contagens] < 0).any().any():
        falhas.append(Falha("dominio", "ouro.relatos_por_hora tem contagem negativa"))
    return falhas


def _unicidade(relatos, por_hora, taxas, qualidade):
    falhas = []
    for tabela, df in (
        (PRATA_RELATOS, relatos),
        (OURO_RELATOS_POR_HORA, por_hora),
        (OURO_TAXAS_POR_LINHA, taxas),
        (OURO_QUALIDADE_DIARIA, qualidade),
    ):
        repetidas = df.duplicated(list(tabela.chave)).sum()
        if repetidas:
            chave = ", ".join(tabela.chave)
            falhas.append(
                Falha(
                    "unicidade",
                    f"{tabela.schema}.{tabela.nome}: {repetidas} chaves ({chave}) repetidas",
                )
            )
    return falhas


def _privacidade():
    falhas = []
    for tabela in TABELAS_OURO:
        proibidas = COLUNAS_IDENTIFICADORAS & set(tabela.nomes)
        if proibidas:
            falhas.append(
                Falha("privacidade", f"ouro.{tabela.nome} tem identificadores: {sorted(proibidas)}")
            )
    return falhas
