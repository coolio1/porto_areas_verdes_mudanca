"""Gera Mobilidade/autocarros.html: mapa das velocidades dos autocarros STCP (ver docs/superpowers/specs/2026-11-11-*)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from velocidade import dados, esperas, habitual, linhas, osm, pagina, trocos  # noqa: E402

TIPOS_DIA = ("util", "fds")


def calcular(pasta_dados: Path, pasta_osm: Path, raio_m: float = 40.0, pasta_stcp: Path | None = None) -> dict:
    """Encadeia leitura → esperas → colagem → agregação para cada (tipo de dia, período)."""
    df = dados.carregar(pasta_dados, pasta_stcp)
    paragens = osm.carregar_paragens(pasta_osm)
    t = linhas.dividir(osm.carregar_rotas(pasta_osm))
    # «Agora» compara velocidade medida com velocidade medida: o habitual só usa a recolha própria
    hab = habitual.por_hora(df[~df.derivada], paragens)
    dias_derivados = int(df[df.derivada].dia.nunique())
    df["espera"] = (esperas.marcar_esperas(df, paragens, raio_m) | esperas.marcar_paradas_longas(df)
                    | esperas.marcar_paradas_em_terminal(df))
    df = linhas.colar(df, t)
    r = {"trocos": t, "agg": {}, "marcadores": {}, "dias": {}, "habitual": hab, "dias_derivados": dias_derivados,
         "coladas_pct": float(df.troco_id.notna().mean() * 100), "intervalo": (df.dia.min(), df.dia.max()), "leituras": df}
    for td in TIPOS_DIA:
        r["dias"][td] = int(df[df.tipo_dia == td].dia.nunique())
        for p in dados.PERIODOS:
            a = trocos.agregar(df, t, p, td)
            r["agg"][(td, p)] = a
            r["marcadores"][(td, p)] = trocos.marcadores(trocos.criticos(a), t)
    return r


def main(argv=None) -> int:
    aqui = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dados", type=Path, default=Path(r"C:\Users\quent\Dados\autocarros"))
    ap.add_argument("--stcp", type=Path, default=None,
                    help="pasta com os CSV diários do pacote de posições da STCP (velocidade derivada, subestima 3–5 km/h); "
                         "por defeito só a recolha própria (decisão 2026-11-13)")
    ap.add_argument("--saida", type=Path, default=aqui / "autocarros.html")
    a = ap.parse_args(argv)
    r = calcular(a.dados, a.dados / "osm", pasta_stcp=a.stcp)
    html = pagina.renderizar(r, aqui / "velocidade" / "template.html")
    a.saida.write_text(html, encoding="utf-8")
    print(f"{a.saida}: {len(html.encode('utf-8')) / 1024 / 1024:.2f} MB; dias {r['dias']}; coladas {r['coladas_pct']:.1f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
