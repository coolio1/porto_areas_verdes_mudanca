"""Extracção da compilação de fichas 2014–2016 (PDF): texto por ficha, com a camada dada pela cor de fundo.

A cor é um preenchimento vectorial (PyMuPDF `get_drawings`), não pixel: não precisa de OCR.
Legenda (página 3 do PDF): branco 2006–2008; verde entidades oficiais; azul Campo Aberto;
amarelo cidadãos e associações; salmão destaques de última hora.
"""
import json
import re
import sys
from pathlib import Path

import pymupdf

RAIZ = Path(__file__).resolve().parents[1]
PDF = RAIZ / "docs" / "fonte_campanha" / "pdf2016" / "111espacos-TOTAL.pdf"
SAIDA = RAIZ / "docs" / "fonte_campanha" / "extraido" / "pdf2016.json"

_CAMADAS = {
    (0.8, 1.0, 0.8): "oficial",
    (0.8, 1.0, 1.0): "campo_aberto",
    (1.0, 1.0, 0.6): "cidadaos",
    (1.0, 0.8, 0.6): "ultima_hora",
}
BASE = "2006-2008"


def classificar_cor(cor) -> str:
    if cor is None or all(abs(c - 1.0) < 0.02 for c in cor):
        return BASE
    for ref, camada in _CAMADAS.items():
        if all(abs(a - b) < 0.03 for a, b in zip(cor, ref)):
            return camada
    return "desconhecida"


def _rects_de_camada(pagina):
    for d in pagina.get_drawings():
        fill = d.get("fill")
        if fill and classificar_cor(fill) not in (BASE, "desconhecida"):
            yield d["rect"], classificar_cor(fill)


def _linhas(pagina):
    for b in pagina.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            texto = "".join(s["text"] for s in l["spans"]).strip()
            if texto:
                yield pymupdf.Rect(l["bbox"]), texto


def _blocos_da_pagina(pagina, n):
    rects = list(_rects_de_camada(pagina))
    blocos = []
    for bbox, texto in _linhas(pagina):
        centro = pymupdf.Point((bbox.x0 + bbox.x1) / 2, (bbox.y0 + bbox.y1) / 2)
        dentro = [(r.get_area(), c) for r, c in rects if centro in r]
        camada = min(dentro)[1] if dentro else BASE
        if blocos and blocos[-1]["camada"] == camada:
            blocos[-1]["texto"] += "\n" + texto
        else:
            blocos.append({"texto": texto, "camada": camada, "pagina": n})
    return blocos


_ID = re.compile(r"C[óo]digo\s*ID\s*(\d{3,5})")
_NOME = re.compile(r"Nome do espa[çc]o\s*(.*)")


def extrair_pdf(caminho, paginas_separadoras=None, paginas=None) -> dict:
    """Devolve {pagina_inicio: {id, titulo, paginas, blocos}}. Chave = página: o mesmo ID pode surgir em dois concelhos."""
    separadoras = set(paginas_separadoras or ())
    doc = pymupdf.open(caminho)
    fichas, actual = {}, None
    for i in (paginas or range(1, len(doc) + 1)):
        pagina = doc[i - 1]
        if i in separadoras:
            actual = None
            continue
        texto = pagina.get_text()
        m = _ID.search(texto)
        if m and "ENQUADRAMENTO" in texto:
            nome = _NOME.search(texto)
            titulo = (nome.group(1).strip() if nome and nome.group(1).strip()
                      else next((t for t in texto.splitlines() if t.strip()), "").strip())
            actual = fichas[i] = {"id": int(m.group(1)), "titulo": titulo, "pagina_inicio": i, "paginas": [], "blocos": []}
        if actual is not None:
            actual["paginas"].append(i)
            actual["blocos"].extend(_blocos_da_pagina(pagina, i))
    return fichas


_ENTRADA = re.compile(r"^(.*?)\s*\.{4,}\s*(\d+)\s*$")


def parse_indice(texto: str) -> dict:
    """Lê o índice: fichas com concelho, página e se foram seleccionadas; páginas separadoras."""
    linhas = [l.strip() for l in texto.splitlines() if l.strip()]
    fichas, separadoras = [], set()
    concelho, seleccionado = None, True
    for i, l in enumerate(linhas):
        m = _ENTRADA.match(l)
        if m:
            nome, pag = m.group(1).strip(), int(m.group(2))
            if nome.upper().startswith("OUTROS ESPA"):
                seleccionado = False
                separadoras.add(pag)
            else:
                fichas.append({"nome": nome, "pagina": pag, "concelho": concelho, "seleccionado": seleccionado})
        elif i + 1 < len(linhas) and linhas[i + 1].isdigit() and not l.isdigit() and l.lower() != "índice":
            concelho, seleccionado = l, True
            separadoras.add(int(linhas[i + 1]))
    return {"fichas": fichas, "separadoras": separadoras}


def _texto_indice(doc, ate_pagina: int) -> str:
    return "".join(doc[i].get_text() for i in range(5, ate_pagina))


if __name__ == "__main__":
    doc = pymupdf.open(PDF)
    primeira = next(i for i in range(1, len(doc) + 1) if "ENQUADRAMENTO" in doc[i - 1].get_text())
    ind = parse_indice(_texto_indice(doc, primeira - 1))
    fichas = extrair_pdf(PDF, paginas_separadoras=ind["separadoras"])
    por_pagina = {e["pagina"]: e for e in ind["fichas"]}
    for f in fichas.values():
        f.update({k: v for k, v in (por_pagina.get(f["pagina_inicio"]) or {}).items() if k != "pagina"})
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({"indice": {**ind, "separadoras": sorted(ind["separadoras"])}, "fichas": fichas}, ensure_ascii=False, indent=1), encoding="utf-8")
    sem_indice = [i for i, f in fichas.items() if "seleccionado" not in f]
    desconhecidas = sum(1 for f in fichas.values() for b in f["blocos"] if b["camada"] == "desconhecida")
    print(f"{len(fichas)} fichas; índice com {len(ind['fichas'])} entradas; sem correspondência no índice: {len(sem_indice)}; blocos 'desconhecida': {desconhecidas}")
