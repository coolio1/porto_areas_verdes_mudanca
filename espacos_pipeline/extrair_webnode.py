"""Extracção da página «Últimos espaços livres no Porto» do site Webnode (2017 em diante)."""
import html as _html
import json
import re
import urllib.request
from pathlib import Path

from espacos_pipeline.modelo import slugify

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "docs" / "fonte_campanha" / "webnode"
SAIDA = RAIZ / "docs" / "fonte_campanha" / "extraido" / "webnode_porto.json"
URL = "https://espacosvivos-grporto-amp.webnode.pt/ultimos-espacos-livres-no-porto/"

_COORD = re.compile(r"WGS84:?\s*(-?\d+[,.]\d+)\s*;\s*(-?\d+[,.]\d+)")
_FREG = re.compile(r"Localiza[çc][ãa]o\s+(freguesias? .*?)(?=\s+(?:Espa[çc]o proposto por|ficha preenchida por|[ÁA]rea aproximada)|$)", re.I)
_PROP = re.compile(r"(?:Espa[çc]o proposto por|ficha preenchida por)\s+(.*?)(?=\s+[ÁA]rea aproximada|$)", re.I)
_AREA = re.compile(r"[ÁA]rea aproximada\s+(.+)$", re.I)
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
    paragrafos = [(("wsw-40" in p and "<b>" in p), _texto(p)) for p in re.findall(r"(?s)<p[^>]*>(.*?)</p>", html)]
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
            m = _COORD.search(linha)
            if m:
                lat, lon = (float(g.replace(",", ".")) for g in m.groups())
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
    pedido = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(pedido, timeout=30).read().decode("utf-8", "replace")
    DESTINO.mkdir(parents=True, exist_ok=True)
    (DESTINO / "ultimos-espacos-livres-no-porto.html").write_text(html, encoding="utf-8")
    dados = extrair_webnode(html)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({"fonte": URL, "espacos": dados}, ensure_ascii=False, indent=1), encoding="utf-8")
    sel = sum(e["seleccionado"] for e in dados)
    print(f"{len(dados)} espaços ({sel} seleccionados, {len(dados) - sel} não); sem coordenadas: {sum('lat' not in e for e in dados)}; sinal de longitude corrigido: {sum(bool(e.get('lon_sinal_corrigido')) for e in dados)}")
