"""3-30-300 · população por edifício e % de residentes que cumprem cada indicador.

Fonte: GHS-POP 2020 (JRC, R2023A, 100 m, Mollweide), a mesma que o mapa de acessibilidade usa via Earth Engine;
aqui lida do ficheiro original (tile R5_C18, descarga pública do JRC), sem suavização. Cada célula de 100 m é
repartida pelos edifícios nela contidos, proporcionalmente à área de implantação × altura (altura média do nDSM
dos píxeis ≥ 2 m na pegada; 9 m se faltar). Só edifícios não residenciais (comerciais, industriais, escolas,
igrejas…) ficam com peso 0, salvo se a célula não tiver mais nenhum. Total calibrado ao Censos 2021
(231 962 residentes; o GHS-POP 2020 dá +4,5 % no concelho: verificado em acessibilidade/layers/pop_corrected.npy).

Limitações declaradas: edifícios dos concelhos vizinhos não entram na repartição (células de fronteira
sobrecarregam um pouco os edifícios do Porto antes da calibração); o GHS-POP é modelado, não contagem.

Saída: <DADOS>\\populacao_edificios.csv (idx, h_m, pop) e a secção «Por residente» em docs/regra_303030_numeros.md.
"""
import csv
import os
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
LIDAR = Path(os.environ.get("PV_LIDAR_DADOS", DADOS / "lidar"))
GHS_ZIP = DADOS / "ghspop" / "GHS_POP_E2020_GLOBE_R2023A_54009_100_V1_0_R5_C18.zip"
GHS_URL = ("https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A/GHS_POP_E2020_GLOBE_R2023A_54009_100/V1-0/tiles/"
           + GHS_ZIP.name)
CENSOS_2021 = 231_962
ALTURA_DEFEITO = 9.0
NAO_RESIDENCIAL = {"commercial", "industrial", "retail", "office", "warehouse", "school", "university", "college", "kindergarten", "hospital",
                   "church", "chapel", "cathedral", "civic", "public", "government", "stadium", "supermarket", "train_station", "transportation",
                   "parking", "sports_hall", "sports_centre", "hangar", "museum", "fire_station", "religious", "mosque", "synagogue", "temple",
                   "data_center", "hotel", "manufacture", "factory"}


def obter():
    """Descarrega o tile GHS-POP (28 MB) se não existir."""
    import requests
    if GHS_ZIP.exists():
        return
    GHS_ZIP.parent.mkdir(parents=True, exist_ok=True)
    parcial = GHS_ZIP.with_name(GHS_ZIP.name + ".part")
    with requests.get(GHS_URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        esperado = int(r.headers["content-length"])
        with open(parcial, "wb") as f:
            for bloco in r.iter_content(1 << 20):
                f.write(bloco)
    if parcial.stat().st_size != esperado:
        raise SystemExit("descarga incompleta: " + str(parcial))
    parcial.replace(GHS_ZIP)


def distribuir(celulas, pop_celula, pesos, residencial):
    """Reparte a população de cada célula pelos edifícios nela contidos.

    celulas: id da célula de cada edifício; pop_celula: {id: população}; pesos: área×altura;
    residencial: bool. Devolve (pop por edifício, população perdida em células sem edifícios).
    """
    celulas = np.asarray(celulas)
    pesos = np.asarray(pesos, float)
    res = np.asarray(residencial, bool)
    pop = np.zeros(len(celulas))
    usadas = set()
    for c in np.unique(celulas):
        idx = np.nonzero(celulas == c)[0]
        w = np.where(res[idx], pesos[idx], 0.0)
        if w.sum() <= 0:
            w = pesos[idx]
        if w.sum() <= 0:
            continue
        pop[idx] = pop_celula.get(c, 0.0) * w / w.sum()
        usadas.add(c)
    perdida = sum(v for k, v in pop_celula.items() if k not in usadas)
    return pop, perdida


def alturas(ed):
    """Altura média (m) por edifício a partir do nDSM (píxeis ≥ 2 m na pegada); NaN se faltar/folha má."""
    import rasterio
    from rasterio import features
    from shapely.geometry import box
    ma = {r["folha"] for r in csv.DictReader(open(DADOS / "copa_folhas.csv", encoding="utf-8")) if int(r["ma"])}
    soma = np.zeros(len(ed)); n = np.zeros(len(ed)); area_px = np.zeros(len(ed))
    mdt_por_caixa = {}
    for p in LIDAR.glob("MDT-50cm-*.tif"):
        with rasterio.open(p) as d:
            mdt_por_caixa[tuple(round(v) for v in d.bounds)] = p
    for p in sorted(LIDAR.glob("MDS-50cm-*.tif")):
        if p.stem in ma:
            continue
        with rasterio.open(p) as d:
            caixa = tuple(round(v) for v in d.bounds)
            mds = d.read(1, masked=True).astype("float32")
            tr, forma, b = d.transform, d.shape, d.bounds
        if caixa not in mdt_por_caixa:
            continue
        with rasterio.open(mdt_por_caixa[caixa]) as d2:
            mdt = d2.read(1, masked=True).astype("float32")
        nd = np.ma.filled(mds - mdt, np.nan)
        sel = np.nonzero(ed.geometry.intersects(box(*b)).values)[0]
        if not len(sel):
            continue
        lab = features.rasterize(((ed.geometry.iloc[i], int(i) + 1) for i in sel), out_shape=forma, transform=tr, fill=0, dtype="int32")
        dentro = lab > 0
        area_px += np.bincount(lab[dentro], minlength=len(ed) + 1)[1:]
        alto = dentro & np.isfinite(nd) & (nd >= 2)
        soma += np.bincount(lab[alto], weights=np.clip(nd[alto], 0, 100), minlength=len(ed) + 1)[1:]
        n += np.bincount(lab[alto], minlength=len(ed) + 1)[1:]
    h = np.where((n >= 0.2 * np.maximum(area_px, 1)) & (n > 0), soma / np.maximum(n, 1), np.nan)
    return h


def main():
    import pandas as pd
    import rasterio
    from pyproj import Transformer
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import numeros
    from edificios import carregar, dentro_do_porto
    obter()
    ed = carregar()
    h = alturas(ed)
    print("alturas do LiDAR: %.1f %% dos edifícios (resto: %.0f m)" % (100 * np.isfinite(h).mean(), ALTURA_DEFEITO))
    h = np.clip(np.where(np.isfinite(h), h, ALTURA_DEFEITO), 3, 60)
    peso = ed.geometry.area.values * h
    res = ~ed["building"].isin(NAO_RESIDENCIAL).values
    rp = ed.geometry.representative_point()
    mx, my = Transformer.from_crs(3763, "ESRI:54009", always_xy=True).transform(rp.x.values, rp.y.values)
    with rasterio.open(f"/vsizip/{GHS_ZIP}/{GHS_ZIP.stem}.tif") as d:
        r, c = rasterio.transform.rowcol(d.transform, mx, my)
        r, c = np.asarray(r), np.asarray(c)
        celulas = r.astype(np.int64) * 100000 + c
        r0, r1, c0, c1 = r.min() - 1, r.max() + 2, c.min() - 1, c.max() + 2
        a = d.read(1, window=((r0, r1), (c0, c1))).astype("float64")
    a = np.where(a < 0, 0, a)
    pop_cel = {}  # só as células com edifícios do Porto (as restantes não são do concelho)
    for k in np.unique(celulas):
        pop_cel[int(k)] = float(a[int(k // 100000) - r0, int(k % 100000) - c0])
    pop, perdida = distribuir(celulas, pop_cel, peso, res)
    pop = np.where(dentro_do_porto(ed), pop, 0.0)   # edifícios fora do concelho não têm residentes contados; a calibração é sobre os de dentro
    bruto = pop.sum()
    pop = pop * CENSOS_2021 / bruto
    print("GHS-POP nas células dos edifícios: %.0f hab (Censos 2021: %d; factor de calibração %.3f; perdida sem edifícios: %.0f)" % (bruto, CENSOS_2021, CENSOS_2021 / bruto, perdida))
    df, b, t, dd, arv = numeros.montar()
    df["h_m"] = np.round(h, 1)
    df["pop"] = np.round(pop, 2)
    df[["idx", "h_m", "pop"]].to_csv(DADOS / "populacao_edificios.csv", index=False)
    w = df["pop"].values
    print("residentes: «3» %.1f %% | «30» %.1f %% | «300» %.1f %% | os três %.1f %% | nenhum %.1f %%" % tuple(100 * np.average(df[k], weights=w) for k in ("c3", "c30", "c300", "todos", "nenhum")))
    L = numeros.tabela(df, b, t, dd, arv, pesos=w)
    md = ["", "## Por residente (GHS-POP 2020 calibrado ao Censos 2021)", "",
          f"% da população ({CENSOS_2021} hab) que vive em edifícios que cumprem cada indicador.", "",
          "| Variante | «3» | «30» | «300» | Os três |", "|---|---:|---:|---:|---:|"]
    md += [f"| {x[0]} | {x[1]:.1f} % | {x[2]:.1f} % | {x[3]:.1f} % | {x[4]:.1f} % |" for x in L]
    md += ["", f"Residentes sem nenhum dos três: {100 * np.average(df.nenhum, weights=w):.1f} %.", ""]
    doc = RAIZ / "docs" / "regra_303030_numeros.md"
    texto = doc.read_text(encoding="utf-8")
    texto = texto.split("\n## Por residente")[0].rstrip("\n") + "\n" + "\n".join(md)
    doc.write_text(texto, encoding="utf-8")


if __name__ == "__main__":
    main()
