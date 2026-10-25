"""Extracção da página «Últimos espaços livres no Porto» do site Webnode (2017 em diante)."""
import html as _html
import json
import re
import urllib.request
from pathlib import Path

from espacos_pipeline.modelo import slugify

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "docs" / "fonte_campanha" / "webnode"
EXTRAIDO = RAIZ / "docs" / "fonte_campanha" / "extraido"
BASE = "https://espacosvivos-grporto-amp.webnode.pt/"
# concelho -> página do Webnode (o Porto tem a página «Últimos espaços livres no Porto»)
PAGINAS = {
    "porto": "ultimos-espacos-livres-no-porto", "vila-nova-de-gaia": "vila-nova-de-gaia", "gondomar": "gondomar", "maia": "maia",
    "matosinhos": "matosinhos", "vila-do-conde": "vila-do-conde", "espinho": "espinho", "valongo": "valongo",
}

_COORD = re.compile(r"WGS84\s*[:;]?\s*(-?\d+[,.]\s*\d+)\s*;\s*(-?\d+[,.]\s*\d+)")
_FREG = re.compile(r"Localiza[çc][ãa]o\s+(freguesias? .*?)(?=\s+(?:Espa[çc]o proposto por|ficha preenchida por|[ÁA]rea apr.?ximada)|$)", re.I)
_PROP = re.compile(r"(?:Espa[çc]o proposto por|ficha preenchida por)\s+(.*?)(?=\s+[ÁA]rea apr.?ximada|$)", re.I)
_AREA = re.compile(r"[ÁA]rea apr.?ximada\s+(.+)$", re.I)
_MARCADOR_NAO_SEL = re.compile(r"OUTROS ESPA[ÇC]OS PROPOSTOS", re.I)


def _texto(p: str) -> str:
    return _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", p.replace("&nbsp;", " ")))).strip()


def area_em_ha(texto: str):
    """Hectares, só se o texto tiver uma única medida (ex. «3ha + 5ha» devolve None)."""
    medidas = re.findall(r"([\d.,]+)\s*(ha|m2|m²)", texto.replace(" ", ""), re.I)
    if len(medidas) != 1:
        return None
    numero, unidade = medidas[0]
    valor = float(numero.replace(".", "").replace(",", ".")) if "," in numero else float(numero)
    return valor if unidade.lower() == "ha" else round(valor / 10000, 4)


def extrair_webnode(html: str) -> list:
    textos = [_texto(p) for p in re.findall(r"(?s)<p[^>]*>(.*?)</p>", html)]
    # título = parágrafo curto seguido da linha «Coordenadas…» (a marcação do título varia entre concelhos)
    paragrafos = [(i + 1 < len(textos) and textos[i + 1].startswith("Coordenadas") and 0 < len(t) < 200, t) for i, t in enumerate(textos)]
    espacos, seleccionado, i = [], True, 0
    while i < len(paragrafos):
        titulo_p, texto = paragrafos[i]
        if _MARCADOR_NAO_SEL.search(texto) and len(texto) < 80:
            seleccionado = False
        elif titulo_p and i + 1 < len(paragrafos) and paragrafos[i + 1][1].startswith("Coordenadas"):
            linha = paragrafos[i + 1][1]
            corpo, j = [], i + 2
            while j < len(paragrafos) and not paragrafos[j][0] and not _MARCADOR_NAO_SEL.search(paragrafos[j][1]):
                corpo.append(paragrafos[j][1])
                j += 1
            e = {"titulo": texto, "slug": slugify(texto), "seleccionado": seleccionado, "texto": "\n".join(t for t in corpo if t)}
            m = _COORD.search(re.sub(r"(\d+),(\d),(\d)(?!\d)", lambda g: f"{g[1]},{g[2]}{g[3]}", linha))  # «41,0,6» (gralha) -> 41,06
            if m:
                lat, lon = (float(re.sub(r"\s", "", g).replace(",", ".")) for g in m.groups())
                e["lon_sinal_corrigido"] = lon > 0
                e["lat"], e["lon"] = lat, -abs(lon)
            for chave, rx in (("freguesia", _FREG), ("proposto_por", _PROP)):
                mm = rx.search(linha)
                if mm:
                    e[chave] = re.sub(r"^freguesias? (?:de |da |do )?", "", mm.group(1).strip(), flags=re.I) if chave == "freguesia" else mm.group(1).strip()
            ma = _AREA.search(linha)
            e["area_texto"] = ma.group(1).strip() if ma else None
            e["area_ha"] = area_em_ha(ma.group(1)) if ma else None
            espacos.append(e)
        i += 1
    return espacos


if __name__ == "__main__":
    import sys

    DESTINO.mkdir(parents=True, exist_ok=True)
    for concelho in sys.argv[1:] or PAGINAS:
        url = BASE + PAGINAS[concelho] + "/"
        pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(pedido, timeout=30).read().decode("utf-8", "replace")
        (DESTINO / f"{PAGINAS[concelho]}.html").write_text(html, encoding="utf-8")
        dados = extrair_webnode(html)
        for e in dados:
            e["concelho"] = concelho
        EXTRAIDO.mkdir(parents=True, exist_ok=True)
        (EXTRAIDO / f"webnode_{concelho}.json").write_text(json.dumps({"fonte": url, "espacos": dados}, ensure_ascii=False, indent=1), encoding="utf-8")
        sel = sum(e["seleccionado"] for e in dados)
        print(f"{concelho}: {len(dados)} espaços ({sel} seleccionados, {len(dados) - sel} não); sem coordenadas: {sum('lat' not in e for e in dados)}; sinal de longitude corrigido: {sum(bool(e.get('lon_sinal_corrigido')) for e in dados)}")
