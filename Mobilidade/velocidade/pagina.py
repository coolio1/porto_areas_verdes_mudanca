"""Converte o resultado do cálculo em dados compactos e preenche o template HTML da página."""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import carto  # noqa: E402
import nav  # noqa: E402

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro",
         "Novembro", "Dezembro"]


def _intervalo_txt(a, b) -> str:
    if (a.year, a.month) == (b.year, b.month):
        dias = f"{a.day}" if a == b else f"{a.day} a {b.day}"
        return f"{dias} de {MESES[a.month - 1]} de {a.year}"
    return f"{a.day} de {MESES[a.month - 1]} a {b.day} de {MESES[b.month - 1]} de {b.year}"


def _dias_txt(n: int) -> str:
    return f"{n} dia" + ("" if n == 1 else "s")


def dados_json(resultado: dict) -> dict:
    """Geometria dos troços usados (uma vez) + por variante `[idx, dir, v, ph, perdido, n]`."""
    t = resultado["trocos"]
    usados = list(dict.fromkeys(i for a in resultado["agg"].values() for i in a.troco_id))
    idx = {tid: k for k, tid in enumerate(usados)}
    variantes = {}
    for (td, p), a in resultado["agg"].items():
        variantes[f"{td}|{p}"] = [
            [idx[r.troco_id], int(r.dir), round(float(r.v), 1), round(float(r.ph), 1), round(float(r.perdido), 1), int(r.n)]
            for r in a.itertuples()]
    marcadores = {
        f"{td}|{p}": [{"lat": round(m["lat"], 5), "lon": round(m["lon"], 5), "rua": m["rua"], "cruzamento": m["cruzamento"],
                       "perdido": round(m["perdido"], 1), "v": round(m["v"], 1)} for m in ms]
        for (td, p), ms in resultado["marcadores"].items()}
    return {
        "trocos": [[[round(la, 5), round(lo, 5)] for la, lo in t.latlon[tid]] for tid in usados],
        "variantes": variantes, "marcadores": marcadores, "dias": dict(resultado["dias"]),
        "intervalo": _intervalo_txt(*resultado["intervalo"]), "coladas_pct": round(resultado["coladas_pct"], 1),
    }


def renderizar(resultado: dict, template: Path) -> str:
    d = dados_json(resultado)
    fds = d["dias"]["fds"]
    sem_amostra = fds < 2                      # o mínimo de amostra exige 2 dias (um fim-de-semana completo)
    botao_fds = ('disabled title="Ainda sem um fim-de-semana completo de dados"' if sem_amostra else "")
    texto_fds = "a partir de 16 de Novembro" if sem_amostra else _dias_txt(fds)
    corpo = (Path(template).read_text(encoding="utf-8")
             .replace("__NAV__", nav.get_nav("Mobilidade/autocarros.html", depth=1)
                      + nav.get_abas_mobilidade("Mobilidade/autocarros.html", depth=1))
             .replace("__DIAS_UTIL__", _dias_txt(d["dias"]["util"]))
             .replace("__FDS_ATRIBUTOS__", botao_fds)
             .replace("__FDS_TEXTO__", texto_fds)
             .replace("__INTERVALO__", d["intervalo"])
             .replace("__COLADAS__", f"{d['coladas_pct']:.1f}".replace(".", ","))
             .replace("__DADOS__", json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")))
    return carto.aplicar_chave(corpo)
