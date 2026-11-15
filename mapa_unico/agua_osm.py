"""Gera layers/agua_osm.png: água do OSM (Douro e outras massas de água) na grelha das layers de contexto.

Fonte: OpenStreetMap (Overpass) — natural=water, waterway=riverbank e relações de água no domínio do mapa.
Grelha: BOUNDS [[41.13, -8.70], [41.19, -8.54]], 2048 x 769 px (igual a layers/municipios.png).
O oceano continua a vir de layers_historico/rio.png; mapa_unico.py junta as duas máscaras.

Uso (a partir de qualquer pasta):  python mapa_unico/agua_osm.py
Só grava se a resposta do Overpass for 200 e trouxer elementos (nunca cacheia falhas).
"""

import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageDraw
from shapely.geometry import LineString
from shapely.ops import polygonize, unary_union

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
import os
SAIDA = Path(os.environ.get("AGUA_SAIDA", RAIZ / "layers" / "agua_osm.png"))

S, W, N, E = 41.13, -8.70, 41.19, -8.54
LARGURA, ALTURA = 2048, 769
SERVIDORES = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
QUERY = f"""[out:json][timeout:90];
(
  way["natural"="water"]({S},{W},{N},{E});
  way["waterway"="riverbank"]({S},{W},{N},{E});
  relation["natural"="water"]({S},{W},{N},{E});
  relation["waterway"="riverbank"]({S},{W},{N},{E});
);
out geom;"""


def obter() -> list:
    ultimo = None
    for url in SERVIDORES:
        try:
            r = requests.post(url, data={"data": QUERY}, headers={"User-Agent": "porto-verde-mapa/1.0"}, timeout=120)
            if r.status_code == 200 and r.json().get("elements"):
                return r.json()["elements"]
            ultimo = f"{url}: HTTP {r.status_code}"
        except Exception as e:  # noqa: BLE001 — tenta o servidor seguinte, mas diz porquê
            ultimo = f"{url}: {e}"
        print("falhou:", ultimo, file=sys.stderr)
        time.sleep(2)
    raise SystemExit(f"Overpass sem resposta válida ({ultimo})")


def px(lat: float, lon: float) -> tuple[float, float]:
    return (lon - W) / (E - W) * LARGURA, (N - lat) / (N - S) * ALTURA


def anel(geom: list) -> list:
    return [px(p["lat"], p["lon"]) for p in geom]


def poligonos(el: dict):
    """Devolve (exteriores, interiores) como listas de anéis em pixéis."""
    if el["type"] == "way":
        g = anel(el.get("geometry", []))
        return ([g], []) if len(g) >= 4 else ([], [])
    fora, dentro = [], []
    for papel, lista in (("outer", fora), ("inner", dentro)):
        linhas = [
            LineString(anel(m["geometry"]))
            for m in el.get("members", [])
            if m.get("role") == papel and m.get("geometry") and len(m["geometry"]) >= 2
        ]
        if linhas:
            for p in polygonize(unary_union(linhas)):
                lista.append(list(p.exterior.coords))
    return fora, dentro


def main() -> None:
    els = obter()
    im = Image.new("L", (LARGURA, ALTURA), 0)
    d = ImageDraw.Draw(im)
    n = 0
    for el in els:
        fora, dentro = poligonos(el)
        for a in fora:
            d.polygon(a, fill=255)
            n += 1
        for a in dentro:
            d.polygon(a, fill=0)
    # os buracos de uma massa não devem apagar água de outra: segunda passagem só com exteriores
    for el in els:
        if el["type"] == "relation":
            continue
        fora, _ = poligonos(el)
        for a in fora:
            d.polygon(a, fill=255)
    rgba = Image.new("RGBA", (LARGURA, ALTURA), (169, 202, 219, 0))
    rgba.putalpha(im)
    SAIDA.parent.mkdir(exist_ok=True)
    rgba.save(SAIDA, optimize=True)
    pct = sum(1 for p in im.getdata() if p) / (LARGURA * ALTURA) * 100
    print(f"{SAIDA.name}: {len(els)} elementos, {n} anéis, {pct:.1f}% da grelha")


if __name__ == "__main__":
    main()
