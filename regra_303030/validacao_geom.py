"""3-30-300 · geometria dos edifícios da amostra de validação (para desenhar sobre a ortofoto).

Lê validacao_pontos.csv (idx) e grava validacao_geom.json: por idx, o contorno exterior do edifício e o
centróide em EPSG:3763. Sem o veredicto do modelo. Uso: python validacao_geom.py   (venv PortoVerde)
"""
import json
import os
import sys
from pathlib import Path

DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))


def main():
    import pandas as pd
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from edificios import carregar
    pts = pd.read_csv(DADOS / "validacao_pontos.csv", encoding="utf-8-sig")
    ed = carregar().to_crs(3763)
    saida = {}
    for i in pts.idx:
        g = ed.geometry.iloc[int(i)]
        p = g.representative_point()
        poly = g.geoms[0] if g.geom_type == "MultiPolygon" else g
        saida[int(i)] = {"x": p.x, "y": p.y, "contorno": [list(c) for c in poly.exterior.coords]}
    (DADOS / "validacao_geom.json").write_text(json.dumps(saida), encoding="utf-8")
    print(len(saida), "edifícios")


if __name__ == "__main__":
    main()
