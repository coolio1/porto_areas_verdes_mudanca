"""3-30-300 · copa por folha LiDAR: nDSM = MDS − MDT, máscara de copa e sinalização das folhas más.

Por folha (1 km, 50 cm) grava em <DADOS>\\copa\\<folha>.tif uma máscara uint8:
  0 = sem copa · 1 = copa (nDSM ≥ ALTURA_COPA fora de pegadas OSM) · 2 = edifício · 255 = fora do concelho / sem dados
e acrescenta uma linha à tabela <DADOS>\\copa_folhas.csv com o diagnóstico (diferença de datas MDS/MDT,
fracção de píxeis com nDSM < −1 m fora de edifícios, copa %, estado).

Folha «má» = datas MDS/MDT afastadas > DIF_DIAS **e** > FRAC_NEG de píxeis com nDSM < −1 m **dispersos**
(fora de manchas contínuas ≥ MIN_AGUA px, que são água: o MDS lê a superfície e o MDT a margem, e o Douro e o
mar dão nDSM negativo mesmo com datas iguais). Folha má: as alturas não são fiáveis e os passos seguintes
ignoram-na ou assinalam-na.

Uso: python copa.py            (todas as folhas em <DADOS>\\lidar; idempotente com --refazer)
"""
import argparse
import csv
import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np

ALTURA_COPA = 3.0   # m
DIF_DIAS = 30       # dias entre datas MDS e MDT
FRAC_NEG = 0.02     # fracção de píxeis (fora de edifícios) com nDSM < −1 m, fora de corpos de água
MIN_AGUA = 10000    # px (2 500 m²): mancha negativa contínua ≥ isto = água (rio/mar), não erro de dados
RAIZ = Path(__file__).resolve().parents[1]
DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
LIDAR = Path(os.environ.get("PV_LIDAR_DADOS", DADOS / "lidar"))
COPA_DIR = DADOS / "copa"
CAMPOS = ["folha", "mds_data", "mdt_data", "dif_dias", "px_concelho", "frac_ndsm_neg", "mediana_telhados_m", "copa_pct", "ma", "motivo"]

SEM_COPA, COPA, EDIFICIO, NODATA = 0, 1, 2, 255


def mascara(ndsm, pegadas, dentro, altura=ALTURA_COPA):
    """Máscara uint8 (ver docstring) a partir de nDSM (NaN = sem dados) e máscaras booleanas."""
    m = np.full(ndsm.shape, NODATA, np.uint8)
    valido = np.isfinite(ndsm) & dentro
    m[valido] = SEM_COPA
    m[valido & (ndsm >= altura) & ~pegadas] = COPA
    m[valido & pegadas] = EDIFICIO
    return m


def _neg_disperso(ndsm, fora, min_agua):
    """Fracção de píxeis (fora de edifícios) com nDSM < −1 m que NÃO estão em manchas contínuas de água."""
    from scipy import ndimage
    n_fora = int(fora.sum())
    if not n_fora:
        return float("nan"), 0
    neg = fora & (ndsm < -1)
    if not neg.any():
        return 0.0, 0
    # dilatar (não fechar: o fecho come os píxeis do bordo da folha, onde o rio a atravessa) para unir a mancha
    lab, n = ndimage.label(ndimage.binary_dilation(neg, iterations=3))
    tam = np.bincount(lab[neg], minlength=n + 1)  # nº de píxeis negativos por mancha
    agua = neg & (tam[lab] >= min_agua)
    return float((neg & ~agua).sum()) / n_fora, int(agua.sum())


def diagnostico(ndsm, pegadas, dentro, dif_dias, min_agua=MIN_AGUA):
    """Devolve (frac_neg_dispersa, mediana_telhados, copa_pct, má, motivo)."""
    valido = np.isfinite(ndsm) & dentro
    fora = valido & ~pegadas
    n_fora = int(fora.sum())
    neg, px_agua = _neg_disperso(ndsm, fora, min_agua)
    tel = ndsm[valido & pegadas]
    telh = float(np.median(tel)) if tel.size else float("nan")
    copa = 100.0 * float((fora & (ndsm >= ALTURA_COPA)).sum()) / max(n_fora, 1)
    ma = bool(dif_dias is not None and dif_dias > DIF_DIAS and neg == neg and neg > FRAC_NEG)
    motivo = ""
    if ma:
        motivo = f"datas {dif_dias} d afastadas e {100 * neg:.1f} % de nDSM<-1 m disperso"
    elif neg == neg and neg > FRAC_NEG:
        motivo = f"{100 * neg:.1f} % de nDSM<-1 m disperso mas datas próximas: verificar"
    elif px_agua:
        motivo = f"{px_agua} px negativos em mancha contínua (água), ignorados"
    return neg, telh, copa, ma, motivo


def datas_catalogo(s, cache=DADOS / "datas_catalogo.json"):
    """Datas por folha (MDS e MDT) do catálogo da DGT; guarda cache para não repetir o login."""
    if cache.exists():
        return {k: date.fromisoformat(v) for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
    from dgt_sessao import BASE
    d = {}
    for col in ("MDS-50cm", "MDT-50cm"):
        r = s.post(f"{BASE}/dgt-be/v1/search", json={"collections": [col], "bbox": [-8.68, 41.14, -8.55, 41.19], "limit": 200}, timeout=90)
        r.raise_for_status()
        for f in r.json()["features"]:
            d[f["id"]] = date.fromisoformat(f["properties"]["datetime"][:10])
    cache.write_text(json.dumps({k: v.isoformat() for k, v in d.items()}), encoding="utf-8")
    return d


def main():
    import geopandas as gpd
    import rasterio
    from rasterio import features
    from shapely.geometry import box

    ap = argparse.ArgumentParser()
    ap.add_argument("--refazer", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dgt_sessao import sessao

    datas = datas_catalogo(sessao())
    ed = gpd.read_file(DADOS / "edificios_osm.gpkg")
    caop = gpd.read_file(RAIZ / "CAOP_Continente_2025-gpkg" / "CAOP2025_municipios.shp")
    poly = caop[caop["dtmn"] == "1312"].to_crs(3763).geometry.iloc[0]
    mdt_por_caixa = {}
    for p in LIDAR.glob("MDT-50cm-*.tif"):
        with rasterio.open(p) as d:
            mdt_por_caixa[tuple(round(v) for v in d.bounds)] = p
    COPA_DIR.mkdir(parents=True, exist_ok=True)
    linhas = []
    for p in sorted(LIDAR.glob("MDS-50cm-*.tif")):
        with rasterio.open(p) as d:
            caixa = tuple(round(v) for v in d.bounds)
            mdt_p = mdt_por_caixa.get(caixa)
            if mdt_p is None:
                print("sem MDT:", p.stem)
                continue
            mds = d.read(1, masked=True).astype("float32")
            tr, forma, b, perfil = d.transform, d.shape, d.bounds, d.profile
        with rasterio.open(mdt_p) as d2:
            mdt = d2.read(1, masked=True).astype("float32")
        nd = mds - mdt
        ndsm = np.ma.filled(nd, np.nan)
        sub = ed[ed.intersects(box(*b))]
        pegadas = features.rasterize(((g, 1) for g in sub.geometry), out_shape=forma, transform=tr, fill=0, dtype="uint8").astype(bool) if len(sub) else np.zeros(forma, bool)
        if not poly.intersects(box(*b)):
            continue
        dentro = features.rasterize([(poly, 1)], out_shape=forma, transform=tr, fill=0, dtype="uint8").astype(bool)
        dm, dt = datas.get(p.stem), datas.get(mdt_p.stem)
        dif = abs((dm - dt).days) if dm and dt else None
        neg, telh, copa, ma, motivo = diagnostico(ndsm, pegadas, dentro, dif)
        saida = COPA_DIR / (p.stem.replace("MDS-50cm-", "copa-") + ".tif")
        if a.refazer or not saida.exists():
            for k in ("blockxsize", "blockysize", "tiled", "interleave", "photometric"):
                perfil.pop(k, None)  # o perfil de origem traz blocos que o GDAL recusa
            perfil.update(dtype="uint8", count=1, nodata=NODATA, compress="deflate")
            with rasterio.open(saida, "w", **perfil) as o:
                o.write(mascara(ndsm, pegadas, dentro), 1)
        linhas.append({"folha": p.stem, "mds_data": dm, "mdt_data": dt, "dif_dias": dif, "px_concelho": int((np.isfinite(ndsm) & dentro).sum()),
                       "frac_ndsm_neg": round(neg, 4) if neg == neg else "", "mediana_telhados_m": round(telh, 1) if telh == telh else "",
                       "copa_pct": round(copa, 1), "ma": int(ma), "motivo": motivo})
        print(p.stem[-17:], "má" if ma else "ok", motivo)
    with open(DADOS / "copa_folhas.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(linhas)
    print("folhas:", len(linhas), "| más:", sum(l["ma"] for l in linhas))


if __name__ == "__main__":
    main()
