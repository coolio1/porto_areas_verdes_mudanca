"""Gera os 5 mapas de fundo da entrada (assets/images/inicio/mapa-*.png) a partir dos dados do mapa único.

Fontes (só do repositório): mapa_unico/dados/*.js (máscaras embutidas), acessibilidade/parques_porto.geojson.
Água = contexto['agua'] (oceano de layers_historico/rio.png + Douro do OSM, layers/agua_osm.png).
Regra visual (maquete P2b «Palco e régua»): o que existe = claro; o que se perdeu = ameixa; rio com margem escura.
Grelha 1400 x 700 px sobre lon -8.70..-8.54, lat 41.13..41.19, recortada à caixa do concelho, largura final 900.
O enquadramento é o mesmo de gerar_inicio.py (LON/LAT, CAIXA): mudar um = mudar os dois.

Uso:  uv run --no-project --with pillow --with numpy --with scipy python gerar_inicio_mapas.py [--saida PASTA]
(por defeito grava em assets/images/inicio/).
Aviso: os PNG publicados vêm da água aprovada na maquete (sem origem documentada); este gerador usa a água do OSM e
reproduz-os com ~2 % de pixéis diferentes (foz do Douro e costa de Gaia). Gerar para outra pasta e comparar antes de
substituir os publicados.
"""
import argparse
import base64
import io
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

RAIZ = Path(__file__).resolve().parent
W, H = 1400, 700
LON0, LON1, LAT0, LAT1 = -8.70, -8.54, 41.13, 41.19
X0, X1, Y0, Y1 = 63, 1300, 36, 596  # caixa do concelho (igual a CAIXA de gerar_inicio.py)
LARGURA = 900
S = 2  # sobreamostragem dos parques

PLATE, LAND, RIO, MARGEM, EDIF = (0xE6, 0xED, 0xEB), (0xFF, 0xFF, 0xFF), (0xA9, 0xCA, 0xDB), (0x5E, 0x8C, 0xA6), (0xD9, 0xDC, 0xE0)
CLARO, PERDA = (0xA3, 0xD2, 0xBD), (0x9B, 0x3F, 0x8C)
PRIVADO, PAGO, PARQUE = (0xD6, 0xC4, 0x96), (0xD9, 0x64, 0x2B), (0x0B, 0x52, 0x32)


def carregar(nome):
    s = (RAIZ / "mapa_unico" / "dados" / f"{nome}.js").read_text(encoding="utf8")
    return json.loads(s[s.index("=") + 1:].strip().rstrip(";"))


def mascara(uri):
    im = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("RGBA").resize((W, H), Image.NEAREST)
    return np.array(im)[..., 3] > 0


def dilatar(m, k=3):
    return np.array(Image.fromarray(m.astype("uint8") * 255).filter(ImageFilter.MaxFilter(k))) > 0


def erodir(m, k=3):
    return np.array(Image.fromarray(m.astype("uint8") * 255).filter(ImageFilter.MinFilter(k))) > 0


def limpar_agua(rio):
    """Só a massa principal (oceano + Douro): tira lagos e ribeiros soltos do OSM (componentes < 3000 px)."""
    rotulos, n = ndimage.label(rio)
    tamanhos = ndimage.sum(rio, rotulos, range(1, n + 1))
    return np.isin(rotulos, 1 + np.nonzero(tamanhos >= 3000)[0])


def px(lon, lat):
    return (lon - LON0) / (LON1 - LON0) * W * S, (LAT1 - lat) / (LAT1 - LAT0) * H * S


def parques():
    im = Image.new("L", (W * S, H * S), 0)
    d = ImageDraw.Draw(im)
    for f in json.loads((RAIZ / "acessibilidade" / "parques_porto.geojson").read_text(encoding="utf8"))["features"]:
        g = f["geometry"]
        for poly in [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]:
            for anel in poly:
                pts = [px(*c[:2]) for c in anel]
                if len(pts) > 2:
                    d.polygon(pts, fill=255)
    return np.array(im.resize((W, H), Image.LANCZOS)) > 100


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--saida", type=Path, default=RAIZ / "assets" / "images" / "inicio")
    a = ap.parse_args()
    a.saida.mkdir(parents=True, exist_ok=True)

    A, C, Hj, Hi, P = (carregar(n) for n in ("acessibilidade", "contexto", "hoje", "historico", "privado"))
    porto = mascara(A["imgs"]["acc"]) | mascara(A["imgs"]["baixa"])
    rio = limpar_agua(mascara(C["agua"]))
    margem = rio & ~erodir(rio)
    pago = mascara(C["pago"]) & porto
    privado = mascara(A["imgs"]["privado"]) & ~mascara(C["pago"]) & porto
    edif = mascara(Hj["uso_edificado"]) & porto
    parque = parques() & porto

    def base(com_edif=True):
        im = np.zeros((H, W, 3), "uint8")
        im[...] = PLATE
        im[rio] = RIO
        im[margem] = MARGEM
        im[porto] = LAND
        if com_edif:
            im[edif] = EDIF
        return im

    def gravar(im, nome):
        img = Image.fromarray(im, "RGB").crop((X0, Y0, X1, Y1))
        img = img.resize((LARGURA, round(img.height * LARGURA / img.width)), Image.LANCZOS)
        img = img.convert("P", palette=Image.ADAPTIVE, colors=40)
        destino = a.saida / f"mapa-{nome}.png"
        img.save(destino, optimize=True)
        print(f"{destino.name}: {img.size}, {os.path.getsize(destino) // 1024} KB")

    im = base(); im[privado] = PRIVADO; im[pago] = PAGO; im[parque] = PARQUE; gravar(im, "camadas")
    im = base(); im[mascara(Hj["uso_arvores"]) & porto] = CLARO; im[dilatar(mascara(Hj["arvores_edificado"]) & porto) & porto] = PERDA; gravar(im, "mudancas")
    im = base(False); im[mascara(Hi["veg_2023-24"]) & porto] = CLARO; im[mascara(Hi["veg_perda"]) & porto] = PERDA; gravar(im, "historico")
    im = base(); im[mascara(P["interior_subsistente"]) & porto] = PRIVADO; im[dilatar(mascara(P["interior_perdido"]) & porto) & porto] = PERDA; gravar(im, "privado")
    gravar(base(False), "base")


if __name__ == "__main__":
    main()
