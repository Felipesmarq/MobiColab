"""Camada bronze (RD03, issue #30): cópia imutável da origem, só acrescentada.

A cada execução, cada tabela da origem é comparada com a versão mais recente
guardada na bronze, pela chave da tabela:

- linha nova ou com conteúdo diferente → entra uma versão nova;
- linha que sumiu da origem → entra uma versão marcada `_apagado_na_origem`;
- linha igual → nada muda.

Nenhuma linha da bronze é editada ou apagada. A prata (próxima camada) usa
a versão mais recente de cada chave.
"""

import hashlib
from pathlib import Path

import pandas as pd
from django.conf import settings
from django.db.models import Case, Value, When
from django.utils import timezone

from dados.mock.gerador import DOMINIO_MOCK
from relatos.models import Confirmacao, Relato
from transporte.models import Linha, LinhaParada, Parada

from . import banco
from .esquemas import (
    BRONZE_CONFIRMACOES,
    BRONZE_EXECUCOES,
    BRONZE_LINHAS,
    BRONZE_LINHAS_PARADAS,
    BRONZE_PARADAS,
    BRONZE_RELATOS,
    BRONZE_TEMPERATURA,
    META_BRONZE,
)

PASTA_EXTERNOS = Path(settings.BASE_DIR).parent / "dados" / "externos"
COLUNAS_TEMPERATURA = {"data_hora", "temperatura_c", "fonte"}
_META = {c.nome for c in META_BRONZE}


def executar(pasta_externos=None, agora=None):
    """Roda a bronze inteira. Devolve {tabela: (linhas lidas, versões novas)}."""
    banco.garantir_schemas()
    agora = agora or timezone.now()
    pasta_externos = Path(pasta_externos or PASTA_EXTERNOS)
    extracoes = [
        (BRONZE_RELATOS, _relatos),
        (BRONZE_CONFIRMACOES, _confirmacoes),
        (BRONZE_LINHAS, _linhas),
        (BRONZE_PARADAS, _paradas),
        (BRONZE_LINHAS_PARADAS, _linhas_paradas),
        (BRONZE_TEMPERATURA, lambda: _temperatura(pasta_externos / "temperatura")),
    ]
    resumo = {}
    execucoes = []
    for tabela, extrair in extracoes:
        lidas, novas = acrescentar_versoes(tabela, extrair(), agora)
        resumo[tabela.nome] = (lidas, novas)
        execucoes.append(
            {
                "extraido_em": agora,
                "tabela": tabela.nome,
                "linhas_lidas": lidas,
                "linhas_novas": novas,
            }
        )
    banco.acrescentar(BRONZE_EXECUCOES, pd.DataFrame(execucoes))
    return resumo


def acrescentar_versoes(tabela, origem, agora):
    """Acrescenta à `tabela` só o que mudou desde a última versão de cada chave."""
    colunas_origem = [n for n in tabela.nomes if n not in _META]
    chave = list(tabela.chave)
    origem = banco.tipar(origem.assign(_apagado_na_origem=False), tabela)
    origem = origem.drop_duplicates(chave, keep="last").reset_index(drop=True)
    origem["_hash"] = impressao_digital(origem, colunas_origem)

    atuais = versoes_atuais(banco.ler(tabela), tabela)

    comparacao = origem.merge(
        atuais[chave + ["_hash"]], on=chave, how="left", suffixes=("", "_atual")
    )
    mudou = comparacao["_hash_atual"].isna() | (comparacao["_hash"] != comparacao["_hash_atual"])
    novas = origem[mudou.to_numpy()]

    vivas = atuais[~atuais["_apagado_na_origem"].fillna(False).astype(bool)]
    sumiram = vivas.merge(origem[chave], on=chave, how="left", indicator=True)
    sumiram = vivas[(sumiram["_merge"] == "left_only").to_numpy()].copy()
    if not sumiram.empty:
        sumiram["_apagado_na_origem"] = True
        sumiram["_hash"] = impressao_digital(sumiram, colunas_origem)

    versoes = pd.concat([novas, sumiram], ignore_index=True) if not sumiram.empty else novas
    versoes = versoes.assign(_extraido_em=agora)
    banco.acrescentar(tabela, versoes)
    return len(origem), len(versoes)


def versoes_atuais(df, tabela):
    """A versão mais recente de cada chave."""
    if df.empty:
        return df
    return df.sort_values("_extraido_em", kind="stable").drop_duplicates(
        list(tabela.chave), keep="last"
    )


def impressao_digital(df, colunas):
    """SHA-1 do conteúdo de cada linha (inclui a marca de apagado)."""
    partes = [df[c].map(_texto_estavel) for c in [*colunas, "_apagado_na_origem"]]
    juntas = (
        pd.concat(partes, axis=1).agg("|".join, axis=1) if len(df) else pd.Series([], dtype=str)
    )
    return juntas.map(lambda s: hashlib.sha1(s.encode("utf-8")).hexdigest())


def _texto_estavel(valor):
    if banco._nulo(valor):
        return "∅"
    if isinstance(valor, pd.Timestamp):
        return valor.tz_convert("UTC").isoformat()
    return str(valor)


# ---------------------------------------------------------------- extrações


def _relatos():
    consulta = Relato.objects.annotate(
        origem=Case(
            When(usuario__email__endswith="@" + DOMINIO_MOCK, then=Value("mock")),
            default=Value("real"),
        )
    ).values(*[n for n in BRONZE_RELATOS.nomes if n not in _META])
    return pd.DataFrame(list(consulta))


def _confirmacoes():
    colunas = [n for n in BRONZE_CONFIRMACOES.nomes if n not in _META]
    return pd.DataFrame(list(Confirmacao.objects.values(*colunas)))


def _linhas():
    colunas = [n for n in BRONZE_LINHAS.nomes if n not in _META]
    return pd.DataFrame(list(Linha.objects.values(*colunas)))


def _paradas():
    colunas = [n for n in BRONZE_PARADAS.nomes if n not in _META]
    return pd.DataFrame(list(Parada.objects.values(*colunas)))


def _linhas_paradas():
    colunas = [n for n in BRONZE_LINHAS_PARADAS.nomes if n not in _META]
    return pd.DataFrame(list(LinhaParada.objects.values(*colunas)))


def _temperatura(pasta):
    arquivos = sorted(Path(pasta).glob("*.csv")) if Path(pasta).exists() else []
    partes = []
    for arquivo in arquivos:
        df = pd.read_csv(arquivo, dtype=str)
        faltando = COLUNAS_TEMPERATURA - set(df.columns)
        if faltando:
            raise ValueError(f"{arquivo.name}: faltam as colunas {', '.join(sorted(faltando))}")
        partes.append(df[sorted(COLUNAS_TEMPERATURA)].assign(arquivo=arquivo.name))
    if not partes:
        return pd.DataFrame(columns=[*sorted(COLUNAS_TEMPERATURA), "arquivo"])
    return pd.concat(partes, ignore_index=True)
