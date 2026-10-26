"""Chave gratuita dos mosaicos CARTO (carto.com/basemaps/apikey).

Desde 2026 o CARTO só serve Positron, Dark Matter e Voyager com chave; sem ela o mosaico
traz a marca de água «API KEY REQUIRED». A chave vem de CARTO_BASEMAPS_KEY no `.env` da raiz
(não vai para o git) e entra nos HTML gerados, onde fica visível, como é normal em mapas públicos.
"""
import os
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
_URL = re.compile(r"""(https://(?:\{s\}\.|[a-c]\.)?basemaps\.cartocdn\.com/[^"'\s<>)]*?\.png)(?!\?key=)""")


def _chave() -> str:
    if os.environ.get("CARTO_BASEMAPS_KEY"):
        return os.environ["CARTO_BASEMAPS_KEY"]
    env = RAIZ / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            nome, _, valor = linha.partition("=")
            if nome.strip() == "CARTO_BASEMAPS_KEY" and valor.strip():
                return valor.strip().strip("\"'")
    raise RuntimeError("Falta CARTO_BASEMAPS_KEY no .env da raiz (chave gratuita em carto.com/basemaps/apikey).")


def aplicar_chave(texto: str) -> str:
    """Acrescenta ?key=… a todos os URLs de mosaicos CARTO em `texto` (idempotente)."""
    chave = _chave()
    return _URL.sub(lambda m: f"{m.group(1)}?key={chave}", texto)


def com_chave(url: str) -> str:
    """O mesmo para um só URL (descarga de mosaicos em Python)."""
    return aplicar_chave(url)
