"""Gera _data/inicio_autocarros.json: a rede de autocarros da página de entrada (index.html, figura «Mobilidade").

Lê só as páginas publicadas da Mobilidade (nunca os dados brutos):
  - Mobilidade/autocarros.html  (const D: troços, velocidades por variante, marcadores, intervalo)
  - Mobilidade/analise.html     (const D: n.º de autocarros e de linhas seguidos)
Mesma regra do modo «Velocidade» de autocarros.html, dias úteis, ponta da tarde («util|pm»): D.variantes já só traz
(troço, sentido) com >= 20 leituras, 3 veículos e 2 dias; o sentido representativo é o mais lento; crítico = < 14 km/h
(pintado por classe); espessura = minutos perdidos por hora (raiz, referência = percentil 95); o resto a cinzento fino.
Só agregados por troço: sem posições nem identificadores de veículo.

Uso (depois de gerar_autocarros.py / gerar_analise.py):  python gerar_inicio.py
O enquadramento (LON/LAT, CAIXA) é o das imagens assets/images/inicio/mapa-*.png: mudar um = mudar os dois.
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
SAIDA = RAIZ / "_data" / "inicio_autocarros.json"
VARIANTE = "util|pm"
CRITICO = 14.0
# grelha 1400 x 700 px sobre lon -8.70..-8.54, lat 41.13..41.19, recortada à caixa do concelho; largura final 900
W, H = 1400, 700
LON0, LON1, LAT0, LAT1 = -8.70, -8.54, 41.13, 41.19
CAIXA = dict(x0=63, x1=1300, y0=36, y1=596)
LARGURA = 900
ORDEM = ["ok", "v3 w1", "v3 w2", "v3 w3", "v2 w1", "v2 w2", "v2 w3", "v1 w1", "v1 w2", "v1 w3"]  # desenho: lentos por cima


def ler_D(pagina):
    t = (RAIZ / pagina).read_text(encoding="utf-8")
    i = t.find("const D = ")
    if i < 0:
        raise SystemExit(f"{pagina}: não encontrei «const D = »")
    return json.JSONDecoder().raw_decode(t[i + 10:])[0]


def percentil(v, p):
    v = sorted(v)
    k = (len(v) - 1) * p
    f = int(k)
    c = min(f + 1, len(v) - 1)
    return v[f] + (v[c] - v[f]) * (k - f)


def intervalo_curto(s):
    """«8 a 13 de Novembro de 2026» -> «8 a 13 Nov. 2026»."""
    m = re.fullmatch(r"(.+?) de (\w+) de (\d{4})", s)
    return f"{m.group(1)} {m.group(2)[:3]}. {m.group(3)}" if m else s


def construir():
    """Os dados da figura, a partir das páginas publicadas da Mobilidade."""
    D = ler_D("Mobilidade/autocarros.html")
    A = ler_D("Mobilidade/analise.html")
    linhas = D["variantes"][VARIANTE]
    por = {}
    for r in linhas:  # r = [troço, sentido, km/h, por hora, min perdidos por hora, leituras] (velocidade/pagina.py)
        por.setdefault(r[0], []).append(r)
    ref = max(1.0, percentil([r[4] for r in linhas], 0.95))
    x0, x1, y0, y1 = CAIXA["x0"], CAIXA["x1"], CAIXA["y0"], CAIXA["y1"]
    esc = LARGURA / (x1 - x0)
    altura = (y1 - y0) * esc

    def xy(lat, lon):
        return (((lon - LON0) / (LON1 - LON0) * W - x0) * esc, ((LAT1 - lat) / (LAT1 - LAT0) * H - y0) * esc)

    caminhos, n_tot, n_crit = {}, 0, 0
    for k, rs in por.items():
        p = min(rs, key=lambda r: r[2])
        crit = p[2] < CRITICO
        n_tot += 1
        n_crit += crit
        pts = [xy(*q) for q in D["trocos"][k]]
        if all(not (-10 < x < LARGURA + 10 and -10 < y < altura + 10) for x, y in pts):
            continue
        if crit:
            c = "v1" if p[2] < CRITICO / 2 else "v2" if p[2] < CRITICO * 0.75 else "v3"
            s = min(1, p[4] / ref) ** 0.5
            chave = c + (" w1" if s < 0.45 else " w2" if s < 0.8 else " w3")
        else:
            chave = "ok"
        if len(pts) > 9:
            pts = pts[::max(1, len(pts) // 8)] + [pts[-1]]
        caminhos.setdefault(chave, []).append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts))

    m = D["marcadores"][VARIANTE][0]
    mx, my = xy(m["lat"], m["lon"])
    out = {
        "_fonte": "gerado por gerar_inicio.py a partir de Mobilidade/autocarros.html e analise.html; não editar à mão",
        "altura": round(altura, 1),
        "camadas": [{"c": k, "d": "".join(caminhos[k])} for k in ORDEM if k in caminhos],
        "n_trocos": f"{n_tot:,}".replace(",", " "),
        "n_criticos": n_crit,
        "intervalo": D["intervalo"],
        "intervalo_curto": intervalo_curto(D["intervalo"]),
        # o nome escreve-se como em autocarros.html: «rua · cruzamento»
        "pior": {"x": round(mx, 1), "y": round(my, 1),
                 "nome": (m["rua"] or "Rua sem nome") + (f" · {m['cruzamento']}" if m.get("cruzamento") else "")},
        "veiculos": A["veiculos"],
        "linhas": A["linhas"],
    }
    return out


def main():
    out = construir()
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{SAIDA.relative_to(RAIZ)}: {out['n_criticos']} de {out['n_trocos']} troços críticos; {out['veiculos']} "
          f"autocarros, {out['linhas']} linhas; {SAIDA.stat().st_size // 1024} KB")


def encadear(saida, esperada):
    """Chamado no fim de gerar_autocarros.py / gerar_analise.py: actualiza o JSON da entrada, mas só quando a página
    gerada é a publicada (com --saida para a scratchpad não mexe em _data/). Devolve 0 se correu bem ou se saltou."""
    if Path(saida).resolve() != Path(esperada).resolve():
        return 0
    try:
        main()
    except Exception as e:  # noqa: BLE001 — diz porquê; o teste test_inicio.py acusa dados velhos
        print(f"AVISO: gerar_inicio.py falhou ({e}); correr `python gerar_inicio.py` à mão", file=__import__('sys').stderr)
        return 1
    return 0


if __name__ == "__main__":
    main()
