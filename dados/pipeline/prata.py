"""Camada prata (RD03, issue #31): dados limpos, reconstruídos do zero a partir da bronze.

O que a prata faz com os relatos, nesta ordem:

1. pega a versão mais recente de cada relato da bronze e descarta os apagados na origem;
2. converte a hora para o fuso America/Recife e deriva data, hora, dia da semana e faixa horária;
3. marca quem fica fora da análise: removidos (RF07), substituídos (RN05) e fora dos domínios
   da RN01 — todos continuam em `prata.relatos_historico`, com o motivo;
4. troca campo opcional vazio por "nao_informado", sem imputar (mecanismo MNAR, RD02);
5. junta os dados da linha (código, modal, operadora, destino, passagem por Terminal Integrado)
   e a contagem de confirmações e contestações.

A temperatura vira uma série horária única: INMET quando houver, mock senão, com lacunas de
até 2 h interpoladas e as maiores deixadas vazias (RD02).
"""

from zoneinfo import ZoneInfo

import pandas as pd
from django.conf import settings

from relatos.models import ArCondicionado, ConfortoTermico, Lotacao, VagaPcd
from transporte.models import Sentido

from . import banco
from .bronze import versoes_atuais
from .esquemas import (
    BRONZE_CONFIRMACOES,
    BRONZE_LINHAS,
    BRONZE_LINHAS_PARADAS,
    BRONZE_PARADAS,
    BRONZE_RELATOS,
    BRONZE_TEMPERATURA,
    META_BRONZE,
    PRATA_CONFIRMACOES,
    PRATA_LINHAS,
    PRATA_RELATOS,
    PRATA_RELATOS_HISTORICO,
    PRATA_TEMPERATURA,
)

FUSO = ZoneInfo(settings.TIME_ZONE)
NAO_INFORMADO = "nao_informado"
OPERADORA_NAO_INFORMADA = "nao_informada"
LACUNA_MAXIMA_HORAS = 2
PRIORIDADE_FONTE_TEMPERATURA = ("inmet", "mock")

# Faixas horárias da análise (hora local, inclusive). Definição do grupo para a EDA e o painel.
FAIXAS_HORARIAS = (
    ("madrugada", 0, 4),
    ("inicio_manha", 5, 5),
    ("pico_manha", 6, 8),
    ("entre_picos", 9, 16),
    ("pico_tarde", 17, 19),
    ("noite", 20, 23),
)

DOMINIOS_OPCIONAIS = {
    "conforto_termico": ConfortoTermico.values,
    "ar_condicionado": ArCondicionado.values,
    "vaga_pcd": VagaPcd.values,
}


def executar():
    """Reconstrói todas as tabelas da prata. Devolve {tabela: linhas gravadas}."""
    banco.garantir_schemas()
    linhas = montar_linhas(
        atuais(banco.ler(BRONZE_LINHAS), BRONZE_LINHAS),
        atuais(banco.ler(BRONZE_LINHAS_PARADAS), BRONZE_LINHAS_PARADAS),
        atuais(banco.ler(BRONZE_PARADAS), BRONZE_PARADAS),
    )
    historico = montar_historico(atuais(banco.ler(BRONZE_RELATOS), BRONZE_RELATOS))
    confirmacoes = montar_confirmacoes(
        atuais(banco.ler(BRONZE_CONFIRMACOES), BRONZE_CONFIRMACOES), historico
    )
    relatos = montar_relatos(historico, linhas, confirmacoes)
    temperatura = montar_temperatura(atuais(banco.ler(BRONZE_TEMPERATURA), BRONZE_TEMPERATURA))

    resumo = {}
    for tabela, df in (
        (PRATA_LINHAS, linhas),
        (PRATA_RELATOS_HISTORICO, historico),
        (PRATA_CONFIRMACOES, confirmacoes),
        (PRATA_RELATOS, relatos),
        (PRATA_TEMPERATURA, temperatura),
    ):
        banco.recriar(tabela, df)
        resumo[tabela.nome] = len(df)
    return resumo


def atuais(df, tabela):
    """Versão mais recente de cada chave, sem as apagadas na origem e sem os metadados."""
    df = versoes_atuais(df, tabela)
    vivas = df[~df["_apagado_na_origem"].fillna(False).astype(bool)]
    return vivas.drop(columns=[c.nome for c in META_BRONZE]).reset_index(drop=True)


def faixa_horaria(hora):
    for nome, inicio, fim in FAIXAS_HORARIAS:
        if inicio <= hora <= fim:
            return nome
    raise ValueError(f"Hora fora de 0–23: {hora}")


def montar_historico(relatos):
    df = relatos.copy()
    local = df["criado_em"].dt.tz_convert(FUSO)
    df["data"] = local.dt.date
    df["hora"] = local.dt.hour.astype("Int64")
    df["dia_semana"] = local.dt.day_of_week.astype("Int64")
    df["fim_de_semana"] = df["dia_semana"] >= 5
    df["faixa_horaria"] = df["hora"].map(faixa_horaria) if len(df) else pd.Series(dtype=object)

    fora = ~df["lotacao"].isin(Lotacao.values) | ~df["sentido"].isin(Sentido.values)
    for coluna, valores in DOMINIOS_OPCIONAIS.items():
        fora |= ~df[coluna].isin([*valores, ""])
        df[coluna] = df[coluna].replace("", NAO_INFORMADO)

    df["prefixo_informado"] = df["prefixo_veiculo"] != ""
    df["removido"] = df["removido_em"].notna()
    df["substituido"] = df["substituido_por_id"].notna()
    df["fora_do_dominio"] = fora
    df["valido"] = ~(df["removido"] | df["substituido"] | df["fora_do_dominio"])
    return banco.tipar(df, PRATA_RELATOS_HISTORICO)


def montar_linhas(linhas, linhas_paradas, paradas):
    df = linhas.copy()
    df["operadora"] = df["operadora"].replace("", OPERADORA_NAO_INFORMADA)

    itinerario = linhas_paradas.merge(
        paradas[["id", "eh_terminal"]].rename(columns={"id": "parada_id"}), on="parada_id"
    )
    terminal = (
        itinerario.assign(eh_terminal=itinerario["eh_terminal"].fillna(False).astype(bool))
        .groupby(["linha_id", "sentido"])["eh_terminal"]
        .any()
    )
    for sentido in Sentido.values:
        por_linha = terminal.xs(sentido, level="sentido") if len(terminal) else pd.Series()
        df[f"passa_por_terminal_{sentido}"] = df["id"].map(por_linha).fillna(False).astype(bool)
    return banco.tipar(df, PRATA_LINHAS)


def montar_confirmacoes(confirmacoes, historico):
    return banco.tipar(
        confirmacoes[confirmacoes["relato_id"].isin(historico["id"])], PRATA_CONFIRMACOES
    )


def montar_relatos(historico, linhas, confirmacoes):
    validos = historico[historico["valido"].astype(bool)].drop(
        columns=["removido", "substituido", "fora_do_dominio", "valido"]
    )
    dados_linha = linhas.rename(
        columns={"id": "linha_id", "codigo": "linha_codigo", "nome": "linha_nome"}
    )[
        [
            "linha_id",
            "linha_codigo",
            "linha_nome",
            "modal",
            "operadora",
            "destino_ida",
            "destino_volta",
            "passa_por_terminal_ida",
            "passa_por_terminal_volta",
        ]
    ]
    df = validos.merge(dados_linha, on="linha_id", how="left")

    ida = df["sentido"] == Sentido.IDA
    volta_sem_destino = df["destino_volta"].fillna("") == ""
    df["destino"] = df["destino_volta"].where(~ida & ~volta_sem_destino, df["destino_ida"])
    df["passa_por_terminal"] = df["passa_por_terminal_ida"].where(
        ida, df["passa_por_terminal_volta"]
    )

    votos = (
        confirmacoes.assign(
            confirmacao=confirmacoes["ainda_vale"].astype(bool),
            contestacao=~confirmacoes["ainda_vale"].astype(bool),
        )
        .groupby("relato_id")[["confirmacao", "contestacao"]]
        .sum()
    )
    df["n_confirmacoes"] = df["id"].map(votos["confirmacao"]).fillna(0)
    df["n_contestacoes"] = df["id"].map(votos["contestacao"]).fillna(0)
    return banco.tipar(df, PRATA_RELATOS)


def montar_temperatura(temperatura):
    if temperatura.empty:
        return banco.vazio(PRATA_TEMPERATURA)

    df = temperatura.copy()
    df["data_hora"] = df["data_hora"].dt.floor("h")
    prioridade = {fonte: i for i, fonte in enumerate(PRIORIDADE_FONTE_TEMPERATURA)}
    df["_prioridade"] = df["fonte"].map(prioridade).fillna(len(prioridade))
    df = df.sort_values(["data_hora", "_prioridade"]).drop_duplicates("data_hora")

    serie = df.set_index("data_hora")["temperatura_c"]
    fontes = df.set_index("data_hora")["fonte"]
    horas = pd.date_range(serie.index.min(), serie.index.max(), freq="h", tz="UTC")
    serie = serie.reindex(horas)
    fontes = fontes.reindex(horas)

    lacuna = serie.isna()
    trecho = (lacuna != lacuna.shift()).cumsum()
    tamanho_lacuna = lacuna.groupby(trecho).transform("sum")
    interpolada = serie.interpolate(method="time", limit_area="inside")
    preencher = lacuna & (tamanho_lacuna <= LACUNA_MAXIMA_HORAS) & interpolada.notna()

    resultado = pd.DataFrame({"data_hora": horas})
    resultado["temperatura_c"] = serie.where(~preencher, interpolada).to_numpy()
    resultado["interpolada"] = preencher.to_numpy()
    resultado["fonte"] = fontes.to_numpy()
    resultado.loc[resultado["interpolada"], "fonte"] = "interpolada"
    resultado["fonte"] = resultado["fonte"].fillna("ausente")
    local = resultado["data_hora"].dt.tz_convert(FUSO)
    resultado["data"] = local.dt.date
    resultado["hora"] = local.dt.hour
    return banco.tipar(resultado, PRATA_TEMPERATURA)
