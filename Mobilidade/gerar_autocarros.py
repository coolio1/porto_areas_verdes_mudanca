"""Gera Mobilidade/autocarros.html: mapa das velocidades dos autocarros STCP (ver docs/superpowers/specs/2026-11-11-*)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from velocidade import dados, esperas, linhas, osm, trocos  # noqa: E402

TIPOS_DIA = ("util", "fds")


def calcular(pasta_dados: Path, pasta_osm: Path, raio_m: float = 40.0) -> dict:
    """Encadeia leitura → esperas → colagem → agregação para cada (tipo de dia, período)."""
    df = dados.carregar(pasta_dados)
    paragens = osm.carregar_paragens(pasta_osm)
    t = linhas.dividir(osm.carregar_rotas(pasta_osm))
    df["espera"] = esperas.marcar_esperas(df, paragens, raio_m) | esperas.marcar_paradas_longas(df)
    df = linhas.colar(df, t)
    r = {"trocos": t, "agg": {}, "marcadores": {}, "dias": {},
         "coladas_pct": float(df.troco_id.notna().mean() * 100), "intervalo": (df.dia.min(), df.dia.max()), "leituras": df}
    for td in TIPOS_DIA:
        r["dias"][td] = int(df[df.tipo_dia == td].dia.nunique())
        for p in dados.PERIODOS:
            a = trocos.agregar(df, t, p, td)
            r["agg"][(td, p)] = a
            r["marcadores"][(td, p)] = trocos.marcadores(trocos.criticos(a), t)
    return r
