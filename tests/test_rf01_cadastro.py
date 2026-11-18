import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_cadastro_cria_conta_por_email_e_autentica(client):
    resposta = client.post(
        reverse("cadastro"),
        {
            "email": "passageira@EXEMPLO.com",
            "password1": "senha-forte-12345",
            "password2": "senha-forte-12345",
        },
    )

    usuario = get_user_model().objects.get(email="passageira@exemplo.com")
    assert resposta.status_code == 302
    assert resposta.headers["Location"] == reverse("inicio")
    assert client.get(reverse("inicio")).wsgi_request.user == usuario


def test_cadastro_recusa_senhas_diferentes(client):
    resposta = client.post(
        reverse("cadastro"),
        {
            "email": "passageira@exemplo.com",
            "password1": "senha-forte-12345",
            "password2": "outra-senha",
        },
    )

    assert resposta.status_code == 200
    assert not get_user_model().objects.exists()


def test_login_usa_email_e_senha_da_conta(client):
    usuario = get_user_model().objects.create_user(
        email="passageira@exemplo.com", password="senha-forte-12345"
    )

    resposta = client.post(
        reverse("login"),
        {"username": usuario.email, "password": "senha-forte-12345"},
    )

    assert resposta.status_code == 302
    assert resposta.headers["Location"] == reverse("inicio")
