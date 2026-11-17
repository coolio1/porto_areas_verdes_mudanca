"""3-30-300 · amostra de validação: 300 edifícios para o utilizador confirmar no terreno/Street View.

Amostra estratificada e reprodutível (semente fixa): 60 edifícios de cada um de 5 estratos — cumprem os três,
nenhum, só o «3», só o «30» e só o «300». Para cada ponto: o veredicto do modelo e as colunas em branco
`ve_3_arvores` (s/n), `copa_30` (s/n), `parque_300m` (s/n) para o utilizador preencher; as linhas vêm
misturadas, para não rotular por estrato.

Saída: <DADOS>\\validacao_300_pontos.csv (idx, coordenadas WGS84, ligação ao Google Maps, colunas em branco) e
validacao_modelo.csv (veredicto do modelo, à parte para não enviesar); nada vai para o repo.
Uso: python validacao.py   (venv PortoVerde)
"""
import os
import sys
from pathlib import Path

import numpy as np

DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))
SEMENTE = 303030
POR_ESTRATO = 60


def amostrar(df, por_estrato=POR_ESTRATO, semente=SEMENTE):
    """Índices (sem repetição) de `por_estrato` edifícios por estrato; estratos que não chegam levam todos."""
    rng = np.random.default_rng(semente)
    estratos = {
        "todos": df.todos,
        "nenhum": df.nenhum,
        "so_3": df.c3 & ~df.c30 & ~df.c300,
        "so_30": df.c30 & ~df.c3 & ~df.c300,
        "so_300": df.c300 & ~df.c3 & ~df.c30,
    }
    usados, saida = set(), []
    for nome, m in estratos.items():
        cand = [i for i in np.nonzero(m.values)[0] if i not in usados]
        esc = rng.choice(cand, size=min(por_estrato, len(cand)), replace=False)
        usados.update(int(i) for i in esc)
        saida += [(int(i), nome) for i in esc]
    return saida


def main():
    import pandas as pd
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from edificios import carregar
    df = pd.read_csv(DADOS / "regra_edificios.csv")
    ed = carregar()
    pts = ed.geometry.representative_point().to_crs(4326)
    linhas = []
    for i, estrato in amostrar(df):
        r = df.iloc[i]
        lat, lon = pts.iloc[i].y, pts.iloc[i].x
        linhas.append({"idx": i, "estrato": estrato, "lat": round(lat, 6), "lon": round(lon, 6),
                       "modelo_n_arvores": int(r.n3), "modelo_copa500_pct": r.copa500, "modelo_parque_a_pe_m": round(min(r.d_rede_05, 9999)),
                       "mapa": f"https://www.google.com/maps/@{lat:.6f},{lon:.6f},19z",
                       "ve_3_arvores": "", "copa_30": "", "parque_300m": "", "notas": ""})
    out = pd.DataFrame(linhas).sample(frac=1, random_state=SEMENTE).reset_index(drop=True)   # ordem aleatória: não rotular por estrato
    # o modelo fica noutro ficheiro: quem rotula não deve ver o veredicto (evita enviesar)
    modelo = ["idx", "estrato", "modelo_n_arvores", "modelo_copa500_pct", "modelo_parque_a_pe_m"]
    out[modelo].to_csv(DADOS / "validacao_modelo.csv", index=False)
    out.drop(columns=modelo[1:]).to_csv(DADOS / "validacao_300_pontos.csv", index=False, encoding="utf-8-sig")
    print(len(out), "pontos;", out.estrato.value_counts().to_dict())


if __name__ == "__main__":
    main()
