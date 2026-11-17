"""3-30-300 · imagens da ortofoto DGT 2025 (25 cm, CC BY 4.0) para a validação visual da amostra.

Escolhe 30 pontos por estrato (ordem misturada de validacao_pontos.csv) e, para cada um, grava 2 PNG em
<DADOS>\\validacao_img\\ : `<idx>_perto.png` (160 m x 160 m a 25 cm, contorno do edifício a amarelo e
faixa de 30 m a ciano: para o «3») e `<idx>_longe.png` (1040 m x 1040 m a 1,3 m/px, círculo de 300 m a
vermelho e de 500 m a amarelo, centrados no edifício: para o «30» e o «300»). As imagens não trazem o
veredicto do modelo. Grava também validacao_subset.json (lista de idx).
Uso: python validacao_imagens.py   (python do sistema: PIL; shapely se existir)
"""
import json
import os
import subprocess
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw

DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
OUT = DADOS / "validacao_img"
URL = "https://geo.dgterritorio.gov.pt/wms/ortos2025/service"
POR_ESTRATO = 30


def obter(cx, cy, meia, px, destino):
    bbox = f"{cx - meia},{cy - meia},{cx + meia},{cy + meia}"
    url = (f"{URL}?service=WMS&version=1.3.0&request=GetMap&layers=Ortos2025-RGB&styles="
           f"&crs=EPSG:3763&bbox={bbox}&width={px}&height={px}&format=image/jpeg")
    tmp = destino.with_suffix(".jpg")
    for _ in range(3):
        r = subprocess.run(["curl.exe", "-s", "-m", "120", "-o", str(tmp), "-w", "%{http_code}", url],
                           capture_output=True, text=True)
        if r.stdout.strip() == "200" and tmp.read_bytes()[:3] == b"\xff\xd8\xff":
            try:
                return Image.open(tmp).convert("RGB")
            except OSError:   # JPEG truncado: repetir
                continue
    raise RuntimeError(f"WMS falhou para {destino.name}")


def px_de(x, y, cx, cy, meia, px):
    return ((x - (cx - meia)) / (2 * meia) * px, ((cy + meia) - y) / (2 * meia) * px)


def main():
    OUT.mkdir(exist_ok=True)
    pts = pd.read_csv(DADOS / "validacao_pontos.csv", encoding="utf-8-sig")
    est = pd.read_csv(DADOS / "validacao_modelo.csv").set_index("idx").estrato
    pts["estrato"] = pts.idx.map(est)
    sub = pts.groupby("estrato", sort=False).head(POR_ESTRATO)
    idxs = [int(i) for i in sub.idx]
    (DADOS / "validacao_subset.json").write_text(json.dumps(idxs), encoding="utf-8")
    geom = json.loads((DADOS / "validacao_geom.json").read_text(encoding="utf-8"))
    try:
        from shapely.geometry import Polygon
    except ImportError:
        Polygon = None
    for n, i in enumerate(idxs, 1):
        g = geom[str(i)]
        cx, cy, ring = g["x"], g["y"], g["contorno"]
        # perto: 160 m a 25 cm
        meia, px = 80, 640
        f = OUT / f"{i}_perto.png"
        if not f.exists():
            im = obter(cx, cy, meia, px, f)
            d = ImageDraw.Draw(im)
            if Polygon is not None:
                b = Polygon(ring).buffer(30)
                if not b.is_empty:
                    d.line([px_de(x, y, cx, cy, meia, px) for x, y in b.exterior.coords], fill=(0, 255, 255), width=2)
            d.line([px_de(x, y, cx, cy, meia, px) for x, y in ring], fill=(255, 255, 0), width=3)
            d.line([(10, px - 14), (10 + 40 / (2 * meia) * px, px - 14)], fill=(255, 255, 255), width=4)  # 40 m
            im.save(f)
        # longe: 1040 m a 1,3 m/px
        meia2, px2 = 520, 800
        f = OUT / f"{i}_longe.png"
        if not f.exists():
            im = obter(cx, cy, meia2, px2, f)
            d = ImageDraw.Draw(im)
            c = px2 / 2
            for raio, cor in ((300, (255, 0, 0)), (500, (255, 255, 0))):
                r = raio / (2 * meia2) * px2
                d.ellipse([c - r, c - r, c + r, c + r], outline=cor, width=2)
            d.ellipse([c - 4, c - 4, c + 4, c + 4], fill=(255, 0, 255))
            im.save(f)
        if n % 25 == 0:
            print(n, "de", len(idxs))
    for j in OUT.glob("*.jpg"):
        j.unlink()
    print("feito:", len(idxs), "pontos,", len(list(OUT.glob("*.png"))), "imagens em", OUT)


if __name__ == "__main__":
    main()
