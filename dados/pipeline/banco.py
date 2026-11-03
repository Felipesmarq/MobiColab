"""Leitura e escrita de DataFrames nos schemas do pipeline (ADR 0026).

Usa a mesma conexão do Django, então roda dentro das mesmas transações do
app e dos testes. No PostgreSQL as camadas são schemas de verdade
(`bronze.relatos`); no SQLite, usado só em desenvolvimento local, o schema
vira prefixo do nome (`bronze__relatos`).
"""

import datetime as dt
import math

import numpy as np
import pandas as pd
from django.db import connection

SCHEMAS = ("bronze", "prata", "ouro")

_TIPOS_SQL = {
    "postgresql": {
        "inteiro": "BIGINT",
        "real": "DOUBLE PRECISION",
        "texto": "TEXT",
        "booleano": "BOOLEAN",
        "data_hora": "TIMESTAMP WITH TIME ZONE",
        "data": "DATE",
    },
    "sqlite": {
        "inteiro": "INTEGER",
        "real": "REAL",
        "texto": "TEXT",
        "booleano": "INTEGER",
        "data_hora": "TEXT",
        "data": "TEXT",
    },
}


def eh_postgres():
    return connection.vendor == "postgresql"


def nome_tabela(tabela):
    if eh_postgres():
        return f'"{tabela.schema}"."{tabela.nome}"'
    return f'"{tabela.schema}__{tabela.nome}"'


def garantir_schemas():
    if eh_postgres():
        with connection.cursor() as cursor:
            for schema in SCHEMAS:
                cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')


def existe(tabela):
    with connection.cursor() as cursor:
        if eh_postgres():
            cursor.execute(
                "SELECT 1 FROM information_schema.tables"
                " WHERE table_schema = %s AND table_name = %s",
                [tabela.schema, tabela.nome],
            )
        else:
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = %s",
                [f"{tabela.schema}__{tabela.nome}"],
            )
        return cursor.fetchone() is not None


def ler(tabela, colunas=None):
    """Lê a tabela inteira (ou só `colunas`) já com os tipos do dicionário de dados."""
    if not existe(tabela):
        return vazio(tabela)
    nomes = colunas or tabela.nomes
    lista = ", ".join(f'"{n}"' for n in nomes)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {lista} FROM {nome_tabela(tabela)}")
        df = pd.DataFrame(cursor.fetchall(), columns=nomes)
    return tipar(df, tabela)


def vazio(tabela):
    return tipar(pd.DataFrame(columns=tabela.nomes), tabela)


def recriar(tabela, df):
    """Apaga e cria de novo a tabela com o conteúdo de `df` (prata e ouro)."""
    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {nome_tabela(tabela)}")
    _criar(tabela)
    _inserir(tabela, df)


def acrescentar(tabela, df):
    """Acrescenta linhas sem tocar nas existentes (bronze)."""
    if not existe(tabela):
        _criar(tabela)
    _inserir(tabela, df)


def tipar(df, tabela):
    """Converte cada coluna para o tipo declarado no dicionário de dados."""
    df = df.copy()
    for coluna in tabela.colunas:
        if coluna.nome not in df:
            df[coluna.nome] = None
        serie = df[coluna.nome]
        if coluna.tipo == "inteiro":
            df[coluna.nome] = pd.to_numeric(serie.map(_numero), errors="coerce").astype("Int64")
        elif coluna.tipo == "real":
            df[coluna.nome] = pd.to_numeric(serie.map(_numero), errors="coerce").astype("float64")
        elif coluna.tipo == "booleano":
            df[coluna.nome] = serie.map(_booleano).astype("boolean")
        elif coluna.tipo == "data_hora":
            df[coluna.nome] = pd.to_datetime(serie, utc=True, format="ISO8601")
        elif coluna.tipo == "data":
            df[coluna.nome] = pd.to_datetime(serie, format="ISO8601").dt.date
        else:
            df[coluna.nome] = serie.map(lambda v: "" if _nulo(v) else str(v)).astype("object")
    return df[tabela.nomes]


def _nulo(valor):
    return (
        valor is None
        or valor is pd.NA
        or valor is pd.NaT
        or (isinstance(valor, float) and math.isnan(valor))
    )


def _numero(valor):
    return None if _nulo(valor) else float(valor)


def _booleano(valor):
    return pd.NA if _nulo(valor) else bool(valor)


def _criar(tabela):
    tipos = _TIPOS_SQL[connection.vendor]
    colunas = ", ".join(f'"{c.nome}" {tipos[c.tipo]}' for c in tabela.colunas)
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE TABLE {nome_tabela(tabela)} ({colunas})")


def _inserir(tabela, df):
    if df.empty:
        return
    df = tipar(df, tabela)
    tipos = {c.nome: c.tipo for c in tabela.colunas}
    linhas = [
        tuple(
            _para_banco(valor, tipos[nome]) for nome, valor in zip(tabela.nomes, linha, strict=True)
        )
        for linha in df.itertuples(index=False, name=None)
    ]
    lista = ", ".join(f'"{n}"' for n in tabela.nomes)
    marcadores = ", ".join(["%s"] * len(tabela.nomes))
    with connection.cursor() as cursor:
        cursor.executemany(
            f"INSERT INTO {nome_tabela(tabela)} ({lista}) VALUES ({marcadores})", linhas
        )


def _para_banco(valor, tipo):
    if _nulo(valor):
        return None
    if tipo == "data_hora":
        momento = pd.Timestamp(valor).tz_convert("UTC").to_pydatetime()
        return momento if eh_postgres() else momento.isoformat()
    if tipo == "data":
        return valor if eh_postgres() else dt.date.isoformat(valor)
    if isinstance(valor, np.integer):
        return int(valor)
    if isinstance(valor, np.floating):
        return float(valor)
    if isinstance(valor, np.bool_):
        return bool(valor)
    return valor
