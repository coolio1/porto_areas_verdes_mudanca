"""Substitui as páginas de mapa antigas por redirecções para o mapa único.

Os links antigos (índice, artigos, favoritos, motores de busca) continuam a funcionar.
Cada stub é só a redirecção (sem menu nem rodapé).

Os geradores antigos (porto_publish.py, acessibilidade_html.py, ...) escrevem nestes
mesmos ficheiros; se algum for corrido, volta a correr este script depois.

Uso:  python mapa_unico/gerar_stubs.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

URL = "https://portoverde.pt/mapa_unico/mapa_unico.html"

# página antiga -> parâmetros do hash no mapa único
STUBS = {
    "mapa/mapa.html": "tema=hoje",
    "acessibilidade/acessibilidade_verde.html": "tema=acessibilidade&vista=actual",
    "acessibilidade/conversao_verde.html": "tema=acessibilidade&vista=propostas",
    "ndvi_historico/ndvi_historico.html": "tema=historico",
    "1947/orto_1947.html": "tema=historico&vista=1947",
    "interiores/interiores_quarteiroes.html": "tema=privado",
}

MODELO = """<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8">
<title>Porto Verde — mapas</title>
<meta name="robots" content="noindex">
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url=../mapa_unico/mapa_unico.html#{hash}">
<style>body{{font:15px 'Segoe UI',Arial,sans-serif;margin:40px;color:#333}}</style>
</head>
<body>
<p>Os mapas do Porto Verde foram reunidos numa só página.
<a href="../mapa_unico/mapa_unico.html#{hash}">Abrir o mapa</a>.</p>
<script>location.replace('../mapa_unico/mapa_unico.html#{hash}');</script>
</body>
</html>
"""


def main() -> None:
    for rel, h in STUBS.items():
        html = MODELO.format(
            url=URL, hash=h
        )
        (RAIZ / rel).write_text(html, encoding="utf-8")
        print(f"{rel} -> #{h}")


if __name__ == "__main__":
    main()
