"""3-30-300 · compara as rotulagens visuais (ortofoto) com o veredicto do modelo.

Lê <DADOS>\\validacao_rotulos.csv (idx, n_arvores, ve_3_arvores, copa_pct, copa_30, parque_300m, conf_*)
e validacao_modelo.csv, junta por idx e imprime, por indicador: concordância, matriz de confusão
(modelo x ortofoto) e, para a copa, o erro médio (modelo - ortofoto) e a correlação.
Uso: python validacao_comparar.py   (venv PortoVerde)
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

DADOS = Path(os.environ.get("PV_REGRA_DADOS", r"S:\3 30 300\dados"))


def comparar(rot, mod):
    """Junta rótulos e modelo; devolve DataFrame com colunas m_3, m_30, m_300 (bool) e r_3, r_30, r_300 (bool)."""
    d = rot.merge(mod, on="idx")
    d["m_3"] = d.modelo_n_arvores >= 3
    d["m_30"] = d.modelo_copa500_pct >= 30
    d["m_300"] = d.modelo_parque_a_pe_m <= 300
    d["r_3"] = d.ve_3_arvores.str.strip().str.lower() == "s"
    d["r_30"] = d.copa_30.str.strip().str.lower() == "s"
    d["r_300"] = d.parque_300m.str.strip().str.lower() == "s"
    return d


def resumo(d, ind):
    m, r = d[f"m_{ind}"], d[f"r_{ind}"]
    return {"n": len(d), "concordancia": round(float((m == r).mean()) * 100, 1),
            "modelo_s_orto_s": int((m & r).sum()), "modelo_s_orto_n": int((m & ~r).sum()),
            "modelo_n_orto_s": int((~m & r).sum()), "modelo_n_orto_n": int((~m & ~r).sum()),
            "%s_modelo" % ind: round(float(m.mean()) * 100, 1), "%s_orto" % ind: round(float(r.mean()) * 100, 1)}


def main():
    rot = pd.read_csv(DADOS / "validacao_rotulos.csv")
    mod = pd.read_csv(DADOS / "validacao_modelo.csv")
    d = comparar(rot, mod)
    for ind in ("3", "30", "300"):
        print(ind, resumo(d, ind))
    print("copa: erro médio modelo-orto (pp)", round(float((d.modelo_copa500_pct - d.copa_pct).mean()), 1),
          "| correlação", round(float(np.corrcoef(d.modelo_copa500_pct, d.copa_pct)[0, 1]), 2))
    print("arvores: erro médio modelo-orto", round(float((d.modelo_n_arvores - d.n_arvores).mean()), 1))
    for ind in ("3", "30", "300"):
        c = d[f"conf_{ind}"]
        for nivel in ("alta", "media", "baixa"):
            s = d[c == nivel]
            if len(s):
                print(f"  conf_{ind}={nivel}: n={len(s)} concordância {round(float((s['m_' + ind] == s['r_' + ind]).mean()) * 100, 1)}%")
    d.to_csv(DADOS / "validacao_resultado.csv", index=False)


if __name__ == "__main__":
    main()
