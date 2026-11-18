"""RD02 — temperatura horária do INMET, estação Recife (issue #26)."""

import csv
import zipfile
from datetime import date

import pandas as pd
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from dados import inmet
from dados.mock.config import carregar_config
from dados.mock.gerador import gerar

CABECALHO = (
    "REGIAO:;NE\nUF:;PE\nESTACAO:;RECIFE\nCODIGO (WMO):;A301\n"
    "LATITUDE:;-8,01888888\nLONGITUDE:;-34,94416666\nALTITUDE:;10\nDATA DE FUNDACAO:;22/12/04\n"
    "Data;Hora UTC;PRECIPITAÇÃO TOTAL, HORÁRIO (mm);"
    "TEMPERATURA DO AR - BULBO SECO, HORARIA (°C);UMIDADE RELATIVA DO AR, HORARIA (%);\n"
)


def _csv_inmet(caminho, linhas):
    corpo = "".join(f"{data};{hora} UTC;0;{temp};70;\n" for data, hora, temp in linhas)
    caminho.write_bytes((CABECALHO + corpo).encode("latin-1"))
    return caminho


@pytest.fixture
def arquivo(tmp_path):
    return _csv_inmet(
        tmp_path / "INMET_NE_PE_A301_RECIFE_01-01-2026_A_31-10-2026.CSV",
        [
            ("2026/10/01", "0000", "25,1"),
            ("2026/10/01", "0100", ""),  # falha da estação
            ("2026/10/01", "0200", "-9999"),  # código de ausência
            ("2026/10/01", "0300", "24,8"),
            ("2026/10/01", "0400", "24,6"),
        ],
    )


def test_le_o_csv_do_inmet_em_utc_e_descarta_ausentes(arquivo):
    serie = inmet.ler_csv(arquivo)

    assert serie["temperatura_c"].tolist() == [25.1, 24.8, 24.6]
    assert serie["data_hora"].iloc[0] == pd.Timestamp("2026-10-01T00:00:00Z")
    assert serie.attrs["estacao"] == "A301"


def test_le_a_estacao_de_dentro_do_zip_anual(arquivo, tmp_path):
    anual = tmp_path / "2026.zip"
    with zipfile.ZipFile(anual, "w") as z:
        z.write(arquivo, arquivo.name)
        z.writestr("INMET_NE_PE_A307_PETROLINA_01-01-2026_A_31-10-2026.CSV", "outra")

    assert len(inmet.ler(anual, estacao="A301")) == 3
    with pytest.raises(ValueError, match="A999"):
        inmet.ler(anual, estacao="A999")


def test_recusa_arquivo_sem_coluna_de_temperatura(tmp_path):
    ruim = tmp_path / "ruim.CSV"
    ruim.write_bytes(b"Data;Hora UTC;OUTRA\n2026/10/01;0000 UTC;1\n")
    with pytest.raises(ValueError, match="BULBO SECO"):
        inmet.ler_csv(ruim)


def test_lacunas_separam_curtas_e_longas():
    horas = pd.date_range("2026-10-01", periods=12, freq="h", tz="UTC")
    presentes = [0, 1, 4, 5, 10, 11]  # lacuna de 2 h (2–3) e de 4 h (6–9)
    serie = pd.DataFrame({"data_hora": horas[presentes], "temperatura_c": 25.0})

    resumo = inmet.lacunas(serie)

    assert resumo["horas_no_periodo"] == 12
    assert resumo["horas_ausentes"] == 6
    assert resumo["lacunas"] == 2
    assert resumo["horas_interpoladas"] == 2  # só a lacuna de até 2 h (RD02, L11)
    assert resumo["horas_que_ficam_ausentes"] == 4
    assert resumo["maior_lacuna_h"] == 4


def test_lacuna_no_inicio_do_arquivo_entra_na_conta(tmp_path):
    """A estação A301 ficou parada de janeiro a maio de 2026: isso precisa aparecer."""
    arquivo = _csv_inmet(
        tmp_path / "parada.CSV",
        [("2026/10/01", f"{h:02d}00", "" if h < 5 else "25,0") for h in range(8)],
    )
    resumo = inmet.lacunas(inmet.ler_csv(arquivo))
    assert resumo["horas_no_periodo"] == 8
    assert resumo["horas_que_ficam_ausentes"] == 5
    assert resumo["maior_lacuna_h"] == 5


def test_comando_grava_no_formato_do_pipeline(arquivo, tmp_path, capsys):
    destino = tmp_path / "temperatura"
    call_command("importar_inmet", str(arquivo), "--pasta", str(destino))

    with open(destino / "inmet_A301.csv", encoding="utf-8") as saida:
        linhas = list(csv.DictReader(saida))
    assert linhas[0] == {
        "data_hora": "2026-10-01T00:00:00+00:00",
        "temperatura_c": "25.1",
        "fonte": "inmet",
    }
    assert len(linhas) == 3
    assert "Lacunas" in capsys.readouterr().out


def test_comando_recusa_arquivo_inexistente(tmp_path):
    with pytest.raises(CommandError, match="não encontrado"):
        call_command("importar_inmet", str(tmp_path / "nada.zip"))


@pytest.mark.django_db
def test_mock_usa_a_temperatura_real_quando_existe(tmp_path, arquivo):
    """O conforto térmico do mock precisa seguir a mesma temperatura que a ouro mostra."""
    call_command("loaddata", "linhas_dev", verbosity=0)
    pasta = tmp_path / "temperatura"
    call_command("importar_inmet", str(arquivo), "--pasta", str(pasta))
    config = carregar_config()
    config.valores["periodo.dias"] = 1
    config.valores["usuarios.quantidade"] = 10

    resultado = gerar(config, fim=date(2026, 9, 30), pasta_temperatura=pasta)

    # 30/09 em Recife vai até 01/10 02:59 UTC: as horas 00h e 03h–04h UTC vêm do INMET.
    assert resultado.horas_temperatura_real == 1  # só 00h UTC (21h local) cai no dia 30/09
    with open(resultado.arquivo_temperatura, encoding="utf-8") as mock:
        assert len(list(csv.DictReader(mock))) == 23  # o mock só cobre as horas sem dado real
