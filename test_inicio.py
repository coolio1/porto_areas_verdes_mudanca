"""A página de entrada: dados dos autocarros em dia e recursos que existem."""
import json
import re
from pathlib import Path

import gerar_inicio

RAIZ = Path(__file__).resolve().parent


def test_dados_dos_autocarros_em_dia_com_a_mobilidade():
    # falha depois de gerar_autocarros.py / gerar_analise.py: correr «python gerar_inicio.py»
    assert json.loads(gerar_inicio.SAIDA.read_text(encoding="utf-8")) == gerar_inicio.construir()


def test_imagens_e_folhas_do_index_existem():
    h = (RAIZ / "index.html").read_text(encoding="utf-8")
    fm = h.split("---")[1]
    imgs = re.findall(r"img: (\S+\.png)", fm) + ["emblema.png", "mapa-base.png", "wordmark-mascara.png"]
    for n in imgs:
        assert (RAIZ / "assets/images/inicio" / n).exists(), n
    for f in re.findall(r'\{\{ site\.baseurl \}\}/(assets/[^"]+\.(?:css|js|jpg|png))"', h):
        assert (RAIZ / f).exists(), f
