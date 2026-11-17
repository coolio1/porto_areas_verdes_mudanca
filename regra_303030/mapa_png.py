"""3-30-300 · máscaras para o mapa único: edifícios que cumprem cada indicador, em PNG de 1 bit.

Grelha equirrectangular de 3 m sobre os limites do mapa único (BOUNDS = [[41.13, −8.70], [41.19, −8.54]]), a mesma
convenção das outras camadas. Edifícios rasterizados com all_touched (um telhado de 6 m não desaparece).
Gera em regra_303030/layers/: todos.png (os três), nenhum.png, c3.png, c30.png, c300.png e numeros.json
(% de edifícios e de residentes, hectares de implantação, por camada). `mapa_unico.py` embute-os em dados/regra.js.

Uso: python mapa_png.py   (venv PortoVerde; precisa de regra_edificios.csv e populacao_edificios.csv em <DADOS>)
"""
import json
import os
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
SAIDA = AQUI / "layers"
S, N, W, E = 41.13, 41.19, -8.70, -8.54
PASSO_M = 3.0
CAMADAS = ("todos", "nenhum", "c3", "c30", "c300")


def png_1bit(mask):
    """Máscara booleana → bytes de PNG de paleta a 1 bit (preto opaco onde True, transparente no resto); sem PIL."""
    h, w = mask.shape
    linhas = np.packbits(mask.astype(np.uint8), axis=1)
    cru = b"".join(b"\x00" + linhas[i].tobytes() for i in range(h))

    def chunk(tipo, dados):
        c = struct.pack(">I", len(dados)) + tipo + dados
        return c + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 1, 3, 0, 0, 0)) + chunk(b"PLTE", bytes(6))
            + chunk(b"tRNS", bytes([0, 255])) + chunk(b"IDAT", zlib.compress(cru, 9)) + chunk(b"IEND", b""))


def grelha(passo_m=PASSO_M):
    """(largura, altura, transformada afim) da grelha equirrectangular de `passo_m` metros."""
    from rasterio.transform import from_bounds
    lat0 = (S + N) / 2
    w = int(np.ceil((E - W) * 111320 * np.cos(np.radians(lat0)) / passo_m))
    h = int(np.ceil((N - S) * 111320 / passo_m))
    return w, h, from_bounds(W, S, E, N, w, h)


def categorias(df):
    """Dicionário nome → máscara booleana por edifício."""
    return {"todos": df.todos.values, "nenhum": df.nenhum.values, "c3": df.c3.values, "c30": df.c30.values, "c300": df.c300.values}


def numeros(df, pop, ha):
    """% de edifícios, % de residentes e hectares de implantação por camada."""
    out = {}
    for k, m in categorias(df).items():
        out[k] = {"edificios_pct": round(100 * float(m.mean()), 1), "residentes_pct": round(100 * float(pop[m].sum() / pop.sum()), 1),
                  "ha": round(float(ha[m].sum()) / 1e4, 1)}
    out["total"] = {"edificios": int(len(df)), "residentes": int(round(float(pop.sum()))), "ha": round(float(ha.sum()) / 1e4, 1)}
    return out


def main():
    import pandas as pd
    import rasterio
    from rasterio import features

    sys.path.insert(0, str(AQUI))
    from edificios import carregar
    ed = carregar()
    df = pd.read_csv(DADOS / "regra_edificios.csv")
    pop = pd.read_csv(DADOS / "populacao_edificios.csv")["pop"].values
    assert len(df) == len(ed) == len(pop)
    w, h, tr = grelha()
    g = ed.to_crs(4326).geometry
    lab = features.rasterize(((geom, i + 1) for i, geom in enumerate(g)), out_shape=(h, w), transform=tr, fill=0, dtype="int32", all_touched=True)
    SAIDA.mkdir(exist_ok=True)
    cats = categorias(df)
    for k, m in cats.items():
        tabela = np.concatenate([[False], m])      # índice 0 = sem edifício
        mask = tabela[lab]
        (SAIDA / f"{k}.png").write_bytes(png_1bit(mask))
        print(k, "%d px" % mask.sum(), "%.0f KB" % (os.path.getsize(SAIDA / f'{k}.png') / 1024))
    n = numeros(df, pop, ed.geometry.area.values)
    n["sens"] = {"c30_limiar25_pct": round(100 * float((df.copa500 >= 25).mean()), 1),    # % de edifícios com o limiar a 25 %
                 "c300_1ha_pct": round(100 * float((df.d_rede_1 <= 300).mean()), 1)}      # % de edifícios com parque ≥ 1 ha
    (SAIDA / "numeros.json").write_text(json.dumps(n, ensure_ascii=False, indent=1), encoding="utf-8")
    print("grelha", w, "x", h)


if __name__ == "__main__":
    main()
