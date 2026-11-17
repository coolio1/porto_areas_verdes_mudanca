"""Controlo de qualidade do LiDAR (MDS − MDT) antes de construir o 3-30-300.

Mede, folha a folha:
  1. datas do catálogo (MDS vs MDT): diferença > 30 dias = risco de alturas falsas;
  2. erro grosseiro: % de píxeis com nDSM < −1 m (MDS abaixo do MDT) fora de edifícios;
  3. altura mediana sobre as pegadas OSM (deve ser a altura dos telhados, não ~0);
  4. cobertura de copa = nDSM ≥ 3 m fora de pegadas, dentro do concelho (compara com o Sentinel-2: 14,2 %);
  5. taxa de detecção das árvores do inventário da Câmara (máx. nDSM ≥ 3 m a ≤ 2 m), por classe de idade.

Saída: tabela por folha em S:\\3 30 300\\dados\\qa_lidar_folhas.csv e resumo impresso.
"""
import csv
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio import features
from shapely.geometry import box

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dgt_sessao import BASE, sessao  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
LIDAR = Path(os.environ.get("PV_LIDAR_DADOS", DADOS / "lidar"))
ALTURA_ARVORE = 3.0
RAIO_ARVORE = 2.0  # m


def datas_catalogo(s):
    d = {}
    for col in ("MDS-50cm", "MDT-50cm"):
        r = s.post(f"{BASE}/dgt-be/v1/search", json={"collections": [col], "bbox": [-8.68, 41.14, -8.55, 41.19], "limit": 200}, timeout=90)
        for f in r.json()["features"]:
            d[f["id"]] = date.fromisoformat(f["properties"]["datetime"][:10])
    return d


def arvores():
    out = []
    with open(DADOS / "arvoredo_cmp.csv", encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh, quotechar="'")
        next(rd)
        for row in rd:
            x, y = (float(v) for v in row[4].split(","))
            out.append((x, y, row[3]))
    return out


def main():
    s = sessao()
    datas = datas_catalogo(s)
    ed = gpd.read_file(DADOS / "edificios_osm.gpkg")
    caop = gpd.read_file(RAIZ / "CAOP_Continente_2025-gpkg" / "CAOP2025_municipios.shp")
    poly = caop[caop["dtmn"] == "1312"].to_crs(3763).geometry.iloc[0]
    arv = arvores()
    mdt_por_caixa = {}
    for p in LIDAR.glob("MDT-50cm-*.tif"):
        with rasterio.open(p) as d:
            mdt_por_caixa[tuple(round(v) for v in d.bounds)] = p
    linhas, det = [], defaultdict(lambda: [0, 0])
    tot_px = tot_copa = tot_base = 0
    for p in sorted(LIDAR.glob("MDS-50cm-*.tif")):
        with rasterio.open(p) as d:
            caixa = tuple(round(v) for v in d.bounds)
            mdt_p = mdt_por_caixa.get(caixa)
            if mdt_p is None:
                linhas.append({"folha": p.stem, "obs": "sem MDT com a mesma caixa"})
                continue
            mds = d.read(1, masked=True).astype("float32")
            tr, forma, b = d.transform, d.shape, d.bounds
        with rasterio.open(mdt_p) as d2:
            mdt = d2.read(1, masked=True).astype("float32")
        ndsm = (mds - mdt)
        ok = ~np.ma.getmaskarray(ndsm)
        ndsm = np.ma.filled(ndsm, np.nan)
        sub = ed[ed.intersects(box(*b))]
        pegadas = features.rasterize(((g, 1) for g in sub.geometry), out_shape=forma, transform=tr, fill=0, dtype="uint8").astype(bool) if len(sub) else np.zeros(forma, bool)
        dentro = features.rasterize([(poly, 1)], out_shape=forma, transform=tr, fill=0, dtype="uint8").astype(bool)
        base = ok & dentro
        fora = base & ~pegadas
        n = int(base.sum())
        neg = float((ndsm[fora] < -1).mean()) if fora.any() else np.nan
        telh = float(np.nanmedian(ndsm[base & pegadas])) if (base & pegadas).any() else np.nan
        copa = int((fora & (ndsm >= ALTURA_ARVORE)).sum())
        tot_px += int(fora.sum())
        tot_copa += copa
        tot_base += n
        id_mds, id_mdt = p.stem, mdt_p.stem
        dm, dt = datas.get(id_mds), datas.get(id_mdt)
        dif = abs((dm - dt).days) if dm and dt else None
        linhas.append({"folha": id_mds, "mds_data": dm, "mdt_data": dt, "dif_dias": dif, "px_concelho": n,
                       "frac_ndsm_neg": round(neg, 4) if neg == neg else "", "mediana_telhados_m": round(telh, 1) if telh == telh else "",
                       "copa_pct": round(100 * copa / max(int(fora.sum()), 1), 1), "obs": ""})
        # árvores do inventário nesta folha
        for x, y, idade in arv:
            if b.left <= x < b.right and b.bottom <= y < b.top:
                c, r_ = ~tr * (x, y)
                k = int(RAIO_ARVORE / 0.5)
                r0, c0 = int(r_), int(c)
                w = ndsm[max(r0 - k, 0): r0 + k + 1, max(c0 - k, 0): c0 + k + 1]
                if np.isfinite(w).any():
                    det[idade][1] += 1
                    det[idade][0] += int(np.nanmax(w) >= ALTURA_ARVORE)
    campos = ["folha", "mds_data", "mdt_data", "dif_dias", "px_concelho", "frac_ndsm_neg", "mediana_telhados_m", "copa_pct", "obs"]
    with open(DADOS / "qa_lidar_folhas.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)
    L = [l for l in linhas if not l["obs"]]
    print("folhas MDS:", len(linhas), "| com par MDT:", len(L))
    difs = [l["dif_dias"] for l in L if l["dif_dias"] is not None]
    print("datas MDS≠MDT: dif>30 d em", sum(x > 30 for x in difs), "folhas de", len(difs), "| dif mediana", int(np.median(difs)), "d")
    print("MDS datas (min/máx):", min(l["mds_data"] for l in L if l["mds_data"]), max(l["mds_data"] for l in L if l["mds_data"]))
    print("copa LiDAR (nDSM≥3 m fora de edifícios) sobre a área fora de edifícios: %.1f %%" % (100 * tot_copa / tot_px))
    print("copa LiDAR sobre TODA a área do concelho (comparável ao Sentinel-2 10 m, 14,2 %%): %.1f %%" % (100 * tot_copa / tot_base))
    neg = [l["frac_ndsm_neg"] for l in L if l["frac_ndsm_neg"] != ""]
    print("píxeis com nDSM<−1 m fora de edifícios: mediana %.2f %% | pior folha %.1f %%" % (100 * np.median(neg), 100 * max(neg)))
    tel = [l["mediana_telhados_m"] for l in L if l["mediana_telhados_m"] != ""]
    print("altura mediana sobre as pegadas OSM: %.1f m (folhas: %.1f a %.1f)" % (np.median(tel), min(tel), max(tel)))
    print("detecção das árvores da Câmara (nDSM≥3 m a ≤2 m):")
    tt = sum(v[1] for v in det.values())
    th = sum(v[0] for v in det.values())
    print("  total: %d de %d = %.1f %%" % (th, tt, 100 * th / max(tt, 1)))
    for k in sorted(det, key=lambda s: int(s.split("-")[0]) if s[:1].isdigit() else 999):
        h, n = det[k]
        if n >= 100:
            print("  idade %-7s %5d árvores  %.1f %%" % (k, n, 100 * h / n))


if __name__ == "__main__":
    main()
