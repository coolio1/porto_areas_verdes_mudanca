"""3-30-300 · junta os três indicadores por edifício e gera os números e a tabela de sensibilidade.

  «3»   n.º de árvores visíveis a ≤ 30 m (vista3.py) ≥ 3
  «30»  copa ≥ 30 % num círculo de 500 m (copa500.py)
  «300» parque ≥ 0,5 ha a ≤ 300 m a pé (rede300.py)

Unidade = edifício (todos os edifícios OSM do Porto sem anexos). A população entra em populacao.py.
Sensibilidade «um parâmetro de cada vez» (as outras ficam na base).

Saída: <DADOS>\\regra_edificios.csv (por edifício) e docs/regra_303030_numeros.md (agregados; vai para o repo).
"""
import os
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
BASE = dict(raio3=30, min_arv=3, copa_pct=30, raio_copa=500, parque_ha=0.5, copa_m2=25, altura=3.0, a_pe=True)


def n3_variante(b, t, d, arv, n_edif, raio3=30, copa_m2=25, altura=3.0):
    """n3 por edifício com árvores filtradas: copas LiDAR < copa_m2 ou < altura saem (as da CMP, sem medida, ficam)."""
    lidar = (arv.origem == "lidar").values
    ok = ~lidar | ((arv.mancha_m2.values >= copa_m2) & (arv.altura_m.values >= altura))
    sel = ok[t] & (d <= raio3)
    return np.bincount(b[sel], minlength=n_edif)


def peso_dentro(df, pesos=None):
    """Pesos por edifício para as médias: 0 fora do concelho (coluna `dentro`), 1 (ou `pesos`) dentro."""
    d = df["dentro"].values.astype(float) if "dentro" in df else np.ones(len(df))
    return d if pesos is None else d * np.asarray(pesos, dtype=float)


def avaliar(df, n3, copa, d300):
    c3, c30, c300 = n3 >= 3, copa, d300
    return c3, c30, c300, c3 & c30 & c300


def tabela(df, b, t, d, arv, pesos=None):
    """Linhas (rótulo, %3, %30, %300, %todos) para a base e cada variante; com `pesos` (população) é % de residentes."""
    n = len(df)
    linhas = []
    w = peso_dentro(df, pesos)

    def linha(rotulo, n3=None, raio_copa=500, pct=30, parque=0.5, a_pe=True):
        n3_ = df.n3.values if n3 is None else n3
        copa = (df[f"copa{raio_copa}"].values >= pct)
        col = ("d_rede_" if a_pe else "d_euc_") + ("05" if parque == 0.5 else "1")
        d300 = df[col].values <= 300
        r = avaliar(df, n3_, copa, d300)
        linhas.append((rotulo, *(100 * np.average(x, weights=w) for x in r)))

    linha("**Base** (30 m · 3 árvores ≥25 m² e ≥3 m · 30 % a 500 m · 0,5 ha a pé)")
    linha("«3» a ≤ 20 m", n3=n3_variante(b, t, d, arv, n, raio3=20))
    linha("«3» só copas LiDAR ≥ 50 m²", n3=n3_variante(b, t, d, arv, n, copa_m2=50))
    linha("«3» só copas LiDAR ≥ 4 m de altura", n3=n3_variante(b, t, d, arv, n, altura=4.0))
    linha("«3» sem bloqueio por edifícios (a ≤ 30 m)", n3=df.n30_sem_bloqueio.values)
    linha("«30» círculo de 400 m", raio_copa=400)
    linha("«30» círculo de 600 m", raio_copa=600)
    linha("«30» limiar 25 %", pct=25)
    linha("«30» limiar 35 %", pct=35)
    linha("«300» parque ≥ 1 ha", parque=1)
    linha("«300» em linha recta (não a pé)", a_pe=False)
    return linhas


def montar():
    import pandas as pd
    from edificios import carregar, dentro_do_porto
    from vista3 import carregar_arvores
    ed = carregar()
    import geopandas as gpd
    e300 = gpd.read_file(DADOS / "edificios_300.gpkg")
    assert len(e300) == len(ed), (len(e300), len(ed))
    rp = ed.geometry.representative_point()
    assert np.allclose(rp.x.values, e300.geometry.x.values) and np.allclose(rp.y.values, e300.geometry.y.values), "ordem dos edifícios diverge de edificios_300.gpkg"
    v = pd.read_csv(DADOS / "vista3_edificios.csv")
    c = pd.read_csv(DADOS / "copa500_edificios.csv")
    df = pd.DataFrame({"idx": np.arange(len(ed)), "osm_id": ed.osm_id.values,
                       "d_rede_05": e300.d_rede_05.values, "d_rede_1": e300.d_rede_1.values,
                       "d_euc_05": e300.d_euc_05.values, "d_euc_1": e300.d_euc_1.values})
    df = df.merge(v[["idx", "n3", "n30_sem_bloqueio"]], on="idx").merge(c, on="idx")
    df["d_rede_05"] = df.d_rede_05.fillna(1e9)   # NaN = além do corte de 1 km
    df["d_rede_1"] = df.d_rede_1.fillna(1e9)
    df["c3"] = df.n3 >= 3
    df["c30"] = df.copa500 >= 30
    df["c300"] = df.d_rede_05 <= 300
    df["todos"] = df.c3 & df.c30 & df.c300
    df["nenhum"] = ~(df.c3 | df.c30 | df.c300)
    df["dentro"] = dentro_do_porto(ed)   # os totais só contam edifícios dentro do concelho
    pares = np.load(DADOS / "vista3_pares.npz")
    return df, pares["b"], pares["t"], pares["d"], carregar_arvores()


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    df, b, t, d, arv = montar()
    df.to_csv(DADOS / "regra_edificios.csv", index=False)
    wd = peso_dentro(df)
    n = int(wd.sum())
    print("edifícios dentro do concelho:", n, "(de %d no OSM)" % len(df))
    print("«3»: %.1f %% | «30»: %.1f %% | «300»: %.1f %% | os três: %.1f %% | nenhum: %.1f %%" % tuple(100 * np.average(df[k], weights=wd) for k in ("c3", "c30", "c300", "todos", "nenhum")))
    L = tabela(df, b, t, d, arv)
    md = ["# 3-30-300 no Porto: números e sensibilidade", "",
          f"Unidade: edifício ({n} edifícios OSM). % de edifícios que cumprem cada indicador; as variantes mudam um parâmetro de cada vez.", "",
          "| Variante | «3» | «30» | «300» | Os três |", "|---|---:|---:|---:|---:|"]
    md += [f"| {r[0]} | {r[1]:.1f} % | {r[2]:.1f} % | {r[3]:.1f} % | {r[4]:.1f} % |" for r in L]
    md += ["", f"Edifícios sem nenhum dos três: {100 * np.average(df.nenhum, weights=wd):.1f} %. "
           f"Edifícios cujo círculo de 500 m sai do concelho (cobertura < 70 %): {100 * np.average(df.cobertura500 < 0.7, weights=wd):.1f} %.", ""]
    (RAIZ / "docs" / "regra_303030_numeros.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
