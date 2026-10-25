"""Dossier por espaço: camadas das fontes lado a lado, para escrever o texto fundido (sem nomes de pessoas)."""
import ast
import json
import re
from pathlib import Path

from espacos_pipeline.modelo import slugify
from espacos_pipeline.reconciliar import RAIZ, _carregar

DESTINO = RAIZ / "docs" / "50espacos" / "dossiers" / "porto"


def _ficha(fontes: dict, fonte: str, slug: str):
    for k, f in fontes.get(fonte, {}).items():
        if k != "_duplicados" and isinstance(f, dict) and (k == slug or slugify(f.get("titulo", "")) == slug):
            return f
    return None


def _descricao(f: dict) -> dict:
    d = f.get("descricao")
    if isinstance(d, str):
        try:
            d = ast.literal_eval(d)
        except (ValueError, SyntaxError):
            d = {"texto": d}
    return d or {}


def montar_dossier(slug: str, fontes: dict) -> str:
    ficha = _ficha(fontes, "zip", slug) or _ficha(fontes, "projecto", slug)
    pdf = next((p for p in fontes.get("pdf", {}).values() if slugify(p.get("titulo", "")) == slug), None)
    web = next((w for w in fontes.get("webnode", []) if slugify(w["titulo"]) == slug), None)
    sel = next((s for s in fontes.get("selecao", []) if slugify(s["nome"]) == slug), None)
    titulo = (ficha or pdf or web or {}).get("titulo", slug)
    out = [f"# Dossier — {titulo}", "", "Fontes por camada (cada uma com a sua data). Não incluir nomes de pessoas nem contactos.", ""]
    if sel:
        out += [f"## Selecção 2009\n- Seleccionado: {sel.get('selecao') or 'não'}; área no livro: {sel.get('area_livro_ha')} ha", ""]
    if ficha:
        out += ["## Ficha 2006–2008 (docx)", f"- Freguesia: {ficha.get('freguesia')}; área: {ficha.get('area_texto')}; tipologia: {ficha.get('tipologia')}"]
        out += [f"### {k}\n{v}" for k, v in _descricao(ficha).items()] + [""]
    if pdf:
        out += ["## PDF 2014–2016, blocos por camada"]
        out += [f"### [{b['camada']}] p.{b['pagina']}\n{b['texto']}" for b in pdf["blocos"]] + [""]
    if web:
        out += ["## Webnode (c. 2017–2020; datas no texto)", web.get("texto", ""), ""]
    return "\n".join(out)


if __name__ == "__main__":
    f = _carregar()
    DESTINO.mkdir(parents=True, exist_ok=True)
    slugs = sorted({slugify(w["titulo"]) for w in f["webnode"]})
    for s in slugs:
        (DESTINO / f"{s}.md").write_text(montar_dossier(s, f), encoding="utf-8")
    print(len(slugs), "dossiers ->", DESTINO)
