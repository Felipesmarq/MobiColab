import zipfile

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from transporte.models import Linha, LinhaParada, Modal, Parada, Sentido

pytestmark = pytest.mark.django_db


def criar_feed(caminho):
    tabelas = {
        "routes.txt": (
            "route_id,agency_id,route_short_name,route_long_name,route_type\n"
            "r1,a1,060,Cidade Universitaria BRT,3\n"
        ),
        "agency.txt": "agency_id,agency_name\na1,Operadora Recife\n",
        "stops.txt": (
            "stop_id,stop_name,stop_lat,stop_lon,location_type\n"
            "s1,Terminal TI Recife,-8.05,-34.9,1\n"
            "s2,Parada Centro,-8.06,-34.88,0\n"
            "s3,Parada B,-8.07,-34.87,0\n"
        ),
        "trips.txt": ("route_id,service_id,trip_id,direction_id\nr1,s,t1,0\nr1,s,t2,1\n"),
        "stop_times.txt": (
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            "t1,08:00:00,08:00:00,s1,1\n"
            "t1,08:10:00,08:10:00,s2,2\n"
            "t2,09:00:00,09:00:00,s2,1\n"
            "t2,09:10:00,09:10:00,s3,2\n"
        ),
    }
    with zipfile.ZipFile(caminho, "w") as feed:
        for nome, conteudo in tabelas.items():
            feed.writestr(nome, conteudo)


def test_importa_linha_paradas_e_percursos_sem_duplicar(tmp_path):
    arquivo = tmp_path / "recife.zip"
    criar_feed(arquivo)

    call_command("importar_gtfs", arquivo, verbosity=0)

    linha = Linha.objects.get(gtfs_route_id="r1")
    assert linha.codigo == "060"
    assert linha.modal == Modal.BRT
    assert linha.operadora == "Operadora Recife"
    assert linha.destino_ida == "Parada Centro"
    assert linha.destino_volta == "Parada B"
    assert Parada.objects.count() == 3
    assert Parada.objects.get(gtfs_stop_id="s1").eh_terminal
    assert list(
        LinhaParada.objects.filter(linha=linha, sentido=Sentido.IDA)
        .order_by("ordem")
        .values_list("parada__gtfs_stop_id", flat=True)
    ) == ["s1", "s2"]

    call_command("importar_gtfs", arquivo, verbosity=0)
    assert Linha.objects.count() == 1
    assert Parada.objects.count() == 3
    assert LinhaParada.objects.count() == 4


def test_feed_incompleto_nao_importa_nada(tmp_path):
    arquivo = tmp_path / "incompleto.zip"
    with zipfile.ZipFile(arquivo, "w") as feed:
        feed.writestr("routes.txt", "route_id,route_type\nr1,3\n")

    with pytest.raises(CommandError, match="arquivos obrigatórios"):
        call_command("importar_gtfs", arquivo)

    assert not Linha.objects.exists()


def test_destino_usa_a_ultima_parada_com_nome_e_sem_codigo(tmp_path):
    """No feed do Grande Recife, a maioria das paradas tem só o código como nome
    (ex.: "130220") e as nomeadas terminam com o código ("Terminal X - 010511")."""
    arquivo = tmp_path / "codigos.zip"
    tabelas = {
        "routes.txt": (
            "route_id,route_short_name,route_long_name,route_type\nr1,018,Brasília Teimosa,3\n"
        ),
        "stops.txt": (
            "stop_id,stop_name,stop_lat,stop_lon\n"
            "010511,Terminal Brasília Teimosa - 010511,-8.08,-34.88\n"
            "180938,Tp Cais De Sta. Rita - Embarque 08 - 180938,-8.06,-34.87\n"
            "130220,130220,-8.05,-34.86\n"
            "130221,130221,-8.04,-34.85\n"
        ),
        "trips.txt": "route_id,service_id,trip_id,direction_id\nr1,s,t1,0\nr1,s,t2,1\n",
        "stop_times.txt": (
            "trip_id,stop_id,stop_sequence\n"
            "t1,010511,1\nt1,180938,2\nt1,130220,3\n"
            "t2,130221,1\nt2,130220,2\n"
        ),
    }
    with zipfile.ZipFile(arquivo, "w") as feed:
        for nome, conteudo in tabelas.items():
            feed.writestr(nome, conteudo)

    call_command("importar_gtfs", arquivo, verbosity=0)

    linha = Linha.objects.get(gtfs_route_id="r1")
    assert linha.destino_ida == "Tp Cais De Sta. Rita - Embarque 08"
    assert linha.destino_volta == "Brasília Teimosa"  # nenhuma parada nomeada: usa a linha
    assert Parada.objects.get(gtfs_stop_id="010511").nome == "Terminal Brasília Teimosa"
    assert Parada.objects.get(gtfs_stop_id="130220").nome == "130220"
