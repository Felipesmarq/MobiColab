"""Settings do MobiColab.

Toda configuração vem de variáveis de ambiente (ver `.env.example` e
docs/decisoes/0018-configuracao-por-ambiente.md).
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent  # src/
RAIZ_DIR = BASE_DIR.parent  # raiz do repositório

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(RAIZ_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "contas",
    "transporte",
    "relatos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "contas.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Recife"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = RAIZ_DIR / "staticfiles"

# Parâmetros das regras de negócio (spec, seção 5). Valores iniciais, a calibrar
# com dados reais (spec, seção 12).
RELATO_MEIA_VIDA_MIN = env.float("RELATO_MEIA_VIDA_MIN", default=15)  # RN02
RELATO_PESO_CONFIRMACAO = env.float("RELATO_PESO_CONFIRMACAO", default=0.5)  # RN02
RELATO_PESO_CONTESTACAO = env.float("RELATO_PESO_CONTESTACAO", default=0.5)  # RN02
RELATO_VALIDADE_MIN = env.int("RELATO_VALIDADE_MIN", default=45)  # RN04
RELATO_INTERVALO_MIN = env.int("RELATO_INTERVALO_MIN", default=10)  # RN05
# "A definir" na spec: valores provisórios só para o código ter um padrão.
PESO_MINIMO = env.float("PESO_MINIMO", default=0.5)  # RN03
LIMIAR_CONTESTACAO = env.int("LIMIAR_CONTESTACAO", default=3)  # RF07
