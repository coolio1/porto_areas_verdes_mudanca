"""Gera Mobilidade/analise.html: análise exploratória dos autocarros STCP (velocidades da recolha própria + atrasos e horários do pacote da STCP)."""
import argparse
import datetime
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent))

import carto  # noqa: E402
import nav  # noqa: E402
from analise import agregar, agregar_stcp  # noqa: E402
from velocidade.pagina import _intervalo_txt  # noqa: E402

ATIPICOS = {d.isoformat() for d in agregar.DIAS_ATIPICOS}
DIAS_RECOLHA_NORMAIS = ["2026-11-09", "2026-11-10", "2026-11-12"]       # dias úteis completos (o 13 está incompleto)


def calcular_tudo(dados: Path, stcp: Path) -> dict:
    """Agregados da recolha própria + agregados do pacote da STCP (sem identificadores de veículo)."""
    r = agregar.calcular(dados, stcp)
    s = agregar_stcp.calcular(stcp, ATIPICOS)
    ref = s.pop("_r")
    s["recolha_x_horario"] = agregar_stcp.calcular_recolha(dados, ref, DIAS_RECOLHA_NORMAIS, sorted(ATIPICOS))
    r["stcp"] = s
    return r


def renderizar(r: dict, template: Path) -> str:
    dias = r["dias"]
    ini, fim = datetime.date.fromisoformat(dias[0]["d"]), datetime.date.fromisoformat(dias[-1]["d"])
    s = r["stcp"]
    corpo = (Path(template).read_text(encoding="utf-8")
             .replace("__NAV__", nav.get_nav("Mobilidade/analise.html", depth=1, rodape="leitura"))
             .replace("__LEITURAS__", f"{r['leituras']:,}".replace(",", " "))
             .replace("__VEICULOS__", str(r["veiculos"])).replace("__LINHAS__", str(r["linhas"]))
             .replace("__INTERVALO__", _intervalo_txt(ini, fim))
             .replace("__PASSAGENS__", f"{s['passagens']:,}".replace(",", " ")).replace("__DIASPACOTE__", str(len(s["dias"])))
             .replace("__DADOS__", json.dumps(r, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")))
    return carto.aplicar_chave(corpo)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dados", type=Path, default=Path(r"C:\Users\quent\Dados\autocarros"))
    ap.add_argument("--stcp", type=Path, default=Path(r"C:\Users\quent\Dados\autocarros\stcp"))
    ap.add_argument("--saida", type=Path, default=AQUI / "analise.html")
    ap.add_argument("--json", type=Path, help="reutilizar agregados já calculados (acelera o desenho da página)")
    ap.add_argument("--guardar-json", type=Path, help="guardar os agregados calculados")
    a = ap.parse_args(argv)
    if a.json:
        r = json.loads(a.json.read_text(encoding="utf-8"))
    else:
        r = calcular_tudo(a.dados, a.stcp)
        if a.guardar_json:
            a.guardar_json.write_text(json.dumps(r, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    html = renderizar(r, AQUI / "analise" / "template.html")
    a.saida.write_text(html, encoding="utf-8")
    print(f"{a.saida}: {len(html.encode('utf-8')) / 1024:.0f} KB; {len(r['dias'])} dias da recolha; {r['stcp']['passagens']} passagens do pacote")
    return 0


if __name__ == "__main__":
    sys.exit(main())
