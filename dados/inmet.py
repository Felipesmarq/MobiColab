"""Temperatura horária do INMET (RD02, issue #26).

O INMET publica um ZIP por ano com um CSV por estação automática
(`portal.inmet.gov.br/dadoshistoricos`). Recife é a estação A301. O CSV vem em
latin-1, separado por `;`, com vírgula decimal, 8 linhas de metadados antes do
cabeçalho, data `AAAA/MM/DD` e hora `HHMM UTC`. Hora sem medição vem vazia ou
com -9999.

Este módulo lê esse formato e devolve a série no formato que a bronze espera
(`data_hora` em UTC, `temperatura_c`, `fonte`), além de medir as lacunas.
"""

import io
import re
import zipfile
from pathlib import Path

import pandas as pd

ESTACAO_RECIFE = "A301"
COLUNA_TEMPERATURA = "TEMPERATURA DO AR - BULBO SECO, HORARIA"
AUSENTE = -9999
LACUNA_INTERPOLAVEL_H = 2  # mesma regra da prata (RD02, decisão L11)


def ler(caminho, estacao=ESTACAO_RECIFE):
    """Lê um CSV do INMET ou o CSV da `estacao` de dentro do ZIP anual."""
    caminho = Path(caminho)
    if not zipfile.is_zipfile(caminho):
        return ler_csv(caminho)
    with zipfile.ZipFile(caminho) as anual:
        nomes = [n for n in anual.namelist() if f"_{estacao}_" in Path(n).name.upper()]
        if not nomes:
            raise ValueError(f"Estação {estacao} não encontrada em {caminho.name}.")
        with anual.open(nomes[0]) as arquivo:
            return ler_csv(io.BytesIO(arquivo.read()), nome=Path(nomes[0]).name)


def ler_csv(arquivo, nome=None):
    """Série horária de temperatura (UTC) de um CSV do INMET, só com as horas medidas."""
    nome = nome or Path(arquivo).name
    bruto = arquivo.read() if hasattr(arquivo, "read") else Path(arquivo).read_bytes()
    linhas = bruto.decode("latin-1").splitlines()

    metadados = {}
    inicio = 0
    for i, linha in enumerate(linhas):
        if linha.upper().startswith("DATA;"):
            inicio = i
            break
        chave, _, valor = linha.partition(";")
        metadados[chave.rstrip(":").strip().upper()] = valor.strip()

    df = pd.read_csv(io.StringIO("\n".join(linhas[inicio:])), sep=";", dtype=str)
    coluna = next((c for c in df.columns if c.upper().startswith(COLUNA_TEMPERATURA)), None)
    if coluna is None:
        raise ValueError(f"{nome}: coluna '{COLUNA_TEMPERATURA}' (BULBO SECO) não encontrada.")
    coluna_hora = next(c for c in df.columns if c.upper().startswith("HORA"))
    coluna_data = df.columns[0]

    hora = df[coluna_hora].str.extract(r"(\d{2}):?(\d{2})")
    data_hora = pd.to_datetime(
        df[coluna_data].str.replace("-", "/") + " " + hora[0] + ":" + hora[1],
        format="%Y/%m/%d %H:%M",
        utc=True,
    )
    temperatura = pd.to_numeric(df[coluna].str.replace(",", "."), errors="coerce")
    periodo_do_arquivo = (data_hora.min(), data_hora.max())
    serie = pd.DataFrame({"data_hora": data_hora, "temperatura_c": temperatura})
    serie = serie[serie["temperatura_c"].notna() & (serie["temperatura_c"] != AUSENTE)]
    serie = serie.sort_values("data_hora").reset_index(drop=True)

    codigo = metadados.get("CODIGO (WMO)") or _codigo_do_nome(nome)
    serie.attrs.update(
        {
            "estacao": codigo,
            "nome_estacao": metadados.get("ESTACAO", ""),
            "periodo_do_arquivo": periodo_do_arquivo,
        }
    )
    return serie


def _codigo_do_nome(nome):
    achado = re.search(r"_(A\d{3})_", nome.upper())
    return achado.group(1) if achado else ""


def lacunas(serie):
    """Mede as horas ausentes no período do arquivo (ou entre a primeira e a última medição).

    Conta também a falta no começo e no fim do arquivo: uma estação parada por meses
    no início do ano aparece como uma lacuna longa, não some do resumo.
    """
    inicio, fim = serie.attrs.get(
        "periodo_do_arquivo", (serie["data_hora"].min(), serie["data_hora"].max())
    )
    horas = pd.date_range(inicio, fim, freq="h")
    presente = pd.Series(horas.isin(serie["data_hora"]), index=horas)
    ausente = ~presente
    trecho = (ausente != ausente.shift()).cumsum()
    tamanhos = ausente.groupby(trecho).sum()
    tamanhos = tamanhos[tamanhos > 0]
    curtas = tamanhos[tamanhos <= LACUNA_INTERPOLAVEL_H]
    return {
        "inicio": horas.min(),
        "fim": horas.max(),
        "horas_no_periodo": len(horas),
        "horas_ausentes": int(ausente.sum()),
        "lacunas": len(tamanhos),
        "horas_interpoladas": int(curtas.sum()),
        "horas_que_ficam_ausentes": int(tamanhos[tamanhos > LACUNA_INTERPOLAVEL_H].sum()),
        "maior_lacuna_h": int(tamanhos.max()) if len(tamanhos) else 0,
        "tamanhos": tamanhos.value_counts().sort_index().to_dict(),
    }


def gravar(serie, pasta):
    """Grava no formato lido pela bronze: `data_hora` (ISO, UTC), `temperatura_c`, `fonte`."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"inmet_{serie.attrs.get('estacao') or 'estacao'}.csv"
    saida = serie.assign(
        data_hora=serie["data_hora"].map(lambda m: m.isoformat()),
        fonte="inmet",
    )
    saida.to_csv(caminho, index=False, columns=["data_hora", "temperatura_c", "fonte"])
    return caminho
