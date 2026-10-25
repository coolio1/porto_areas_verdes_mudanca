"""Dossier por espaço: camadas das fontes lado a lado, para escrever o texto fundido (sem nomes de pessoas)."""
import ast
import json
import re
from pathlib import Path

from espacos_pipeline.modelo import slugify
from espacos_pipeline.reconciliar import RAIZ, _carregar, concelho_do_registo



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


def montar_dossier(slug: str, fontes: dict, titulos: dict = None) -> str:
    """`titulos`: título do espaço em cada fonte (do registo reconciliado); sem ele usa-se o slug em todas."""
    t = lambda *chaves: next((slugify(titulos[c]) for c in chaves if titulos and titulos.get(c)), slug)
    ficha = _ficha(fontes, "zip", t("zip", "projecto")) or _ficha(fontes, "projecto", t("projecto", "zip"))
    pdf = next((p for p in fontes.get("pdf", {}).values() if slugify(p.get("titulo", "")) == t("pdf")), None)
    web = next((w for w in fontes.get("webnode", []) if slugify(w["titulo"]) == t("webnode")), None)
    sel = next((s for s in fontes.get("selecao", []) if slugify(s["nome"]) == t("selecao")), None)
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
    from espacos_pipeline.modelo import CONCELHOS
    from espacos_pipeline.reconciliar import reconciliar, resolver

    f = _carregar()
    rel = reconciliar(f)
    resolver(rel)
    n = 0
    for reg in rel.registos:
        concelho = concelho_do_registo(reg)
        titulo = reg["titulo"].get("webnode") or reg["titulo"].get("pdf") or next(iter(reg["titulo"].values()))
        destino = RAIZ / "docs" / "50espacos" / "dossiers" / concelho
        destino.mkdir(parents=True, exist_ok=True)
        (destino / f"{slugify(titulo)}.md").write_text(montar_dossier(slugify(titulo), f, reg["titulo"]), encoding="utf-8")
        n += 1
    print(n, "dossiers ->", RAIZ / "docs" / "50espacos" / "dossiers")
