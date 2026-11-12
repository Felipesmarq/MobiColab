"""Gera `src/static/css/tailwind.css` com o Tailwind CLI standalone (ADR 0027).

Uso: `python scripts/tailwind.py` (uma vez) ou `python scripts/tailwind.py --watch`.
Baixa o binário na primeira execução para `.tools/` (ignorado pelo git). O CSS gerado
é versionado, então rodar o app e os testes não exige o binário.
"""

import platform
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

VERSAO = "v4.1.11"
RAIZ = Path(__file__).resolve().parent.parent
FERRAMENTAS = RAIZ / ".tools"
ENTRADA = RAIZ / "tailwind" / "entrada.css"
SAIDA = RAIZ / "src" / "static" / "css" / "tailwind.css"

PLATAFORMAS = {
    ("Windows", "AMD64"): "windows-x64.exe",
    ("Linux", "x86_64"): "linux-x64",
    ("Linux", "aarch64"): "linux-arm64",
    ("Darwin", "x86_64"): "macos-x64",
    ("Darwin", "arm64"): "macos-arm64",
}


def baixar_binario() -> Path:
    chave = (platform.system(), platform.machine())
    if chave not in PLATAFORMAS:
        sys.exit(f"Plataforma sem binário do Tailwind: {chave}")
    sufixo = PLATAFORMAS[chave]
    destino = FERRAMENTAS / ("tailwindcss.exe" if sufixo.endswith(".exe") else "tailwindcss")
    if not destino.exists():
        FERRAMENTAS.mkdir(exist_ok=True)
        url = (
            "https://github.com/tailwindlabs/tailwindcss/releases/download/"
            f"{VERSAO}/tailwindcss-{sufixo}"
        )
        print(f"Baixando {url}")
        urllib.request.urlretrieve(url, destino)  # noqa: S310 - URL fixa, https
        destino.chmod(destino.stat().st_mode | stat.S_IEXEC)
    return destino


def main() -> int:
    comando = [
        str(baixar_binario()),
        "-i", str(ENTRADA),
        "-o", str(SAIDA),
        "--minify",
        *sys.argv[1:],
    ]  # fmt: skip
    return subprocess.call(comando, cwd=RAIZ)


if __name__ == "__main__":
    sys.exit(main())
