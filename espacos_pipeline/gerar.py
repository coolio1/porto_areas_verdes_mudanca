"""Gera `_espacos/<concelho>/<slug>.md` e `_data/espacos_mapa.json` a partir dos espaços reconciliados e dos textos fundidos revistos."""
import json
import re
from pathlib import Path

from espacos_pipeline.extrair_webnode import area_em_ha
from espacos_pipeline.modelo import CONCELHOS, Espaco, slugify, validar_lote
from espacos_pipeline.reconciliar import RAIZ, _carregar, concelho_do_registo, reconciliar, resolver

FUSAO = RAIZ / "docs" / "50espacos" / "fusao"
ROTULO = {"zip": "Ficha de 2006–2008", "pdf": "Compilação 2014–2016 (PDF de 2018)", "webnode": "Webnode da campanha", "selecao": "Lista de Abril de 2009"}
# Título mostrado no site, quando difere do das fontes; o slug (endereço e pasta de fotos) continua o do título original.
TITULO_PUBLICO = {"barrinha-de-esmoriz-e-lagoa-de-paramos-belp": "Barrinha de Esmoriz e Lagoa de Paramos"}
CAMPOS = ("titulo", "concelho", "freguesia", "seleccionado", "selecao", "area_ha", "n_ficha", "lat", "lon", "origem_coord", "estado_actual", "data_verificacao")


def ler_fusao(caminho: Path):
    """Corpo do texto fundido, só se revisto: true; senão None."""
    partes = Path(caminho).read_text(encoding="utf-8").split("---", 2)
    if len(partes) < 3 or not re.search(r"^revisto:\s*true\s*$", partes[1], re.M):
        return None
    return partes[2].strip()


def listar_media(slug: str, raiz: Path):
    """(fotos, anexos) a partir de 50espacos/media/<slug>/, com caminhos absolutos do site."""
    pasta = Path(raiz) / "50espacos" / "media" / slug
    if not pasta.is_dir():
        return [], []
    url = lambda p: f"/50espacos/media/{slug}/{p.name}"
    ficheiros = sorted(pasta.iterdir())
    fotos = [{"src": url(p)} for p in ficheiros if p.suffix.lower() in (".jpg", ".jpeg")]
    anexos = [{"src": url(p), "titulo": p.stem.replace("_", " ")} for p in ficheiros if p.suffix.lower() == ".pdf"]
    return fotos, anexos


def _escalar(v) -> str:
    """Escalar YAML; cadeias com caracteres especiais vão entre aspas (JSON é YAML válido)."""
    if isinstance(v, str) and not re.search(r"[:#\[\]{}&*!|>'\"%@`]|^[\s?-]|\s$", v):
        return v
    return json.dumps(v, ensure_ascii=False)


def _titulo(e: Espaco) -> str:
    return TITULO_PUBLICO.get(e.slug, e.titulo)


def _pagina(e: Espaco) -> str:
    linhas = ["---", f"title: {_escalar(_titulo(e))}"]
    for campo in CAMPOS:
        v = _titulo(e) if campo == "titulo" else getattr(e, campo)
        if v not in (None, ""):
            linhas.append(f"{campo}: {_escalar(v)}")
    for lista in ("fotos", "anexos", "fontes"):
        itens = getattr(e, lista)
        if itens:
            linhas.append(f"{lista}: {json.dumps(itens, ensure_ascii=False)}")
    return "\n".join(linhas + ["---", e.texto, ""])


def gerar(espacos: list, raiz: Path) -> list:
    erros = validar_lote(espacos)
    if erros:
        raise ValueError("; ".join(erros))
    raiz = Path(raiz)
    escritos = []
    for e in espacos:
        p = raiz / "_espacos" / slugify(e.concelho) / f"{e.slug}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_pagina(e), encoding="utf-8", newline="\n")
        escritos.append(p)
    pontos = [{"slug": e.slug, "titulo": _titulo(e), "lat": e.lat, "lon": e.lon, "origem_coord": e.origem_coord,
               "seleccionado": e.seleccionado, "concelho": slugify(e.concelho)} for e in espacos if e.lat is not None]
    d = raiz / "_data" / "espacos_mapa.json"
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text(json.dumps(sorted(pontos, key=lambda p: p["slug"]), ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return escritos + [d]


def espacos_do_concelho(concelho: str, fontes: dict = None) -> list:
    """Espaços de um concelho (slug canónico) reconciliados, com o texto fundido revisto (sem texto se ainda não revisto)."""
    fontes = fontes or _carregar()
    rel = reconciliar(fontes)
    resolver(rel)
    saida = []
    for reg in rel.registos:
        if concelho_do_registo(reg) != concelho:
            continue
        titulo = reg["titulo"].get("webnode") or reg["titulo"].get("pdf") or next(iter(reg["titulo"].values()))
        res = reg["resolvido"]
        coord = res.get("coordenadas")
        # origem: a ficha de 2006–2008 (docx/PDF) tem prioridade sobre o Webnode
        fonte_coord = next((f for f, v in reg["coordenadas"].items() if coord and list(v) == coord and f != "webnode"), "webnode") if coord else None
        sel = next((s for s in fontes["selecao"] if s["nome"] == reg["titulo"].get("selecao")), None)
        selecao = sel.get("selecao") if sel else None
        ficha = next((f for n in ("zip", "projecto") for f in fontes[n].values() if isinstance(f, dict) and f.get("titulo") in (reg["titulo"].get("zip"), reg["titulo"].get("projecto"))), None)
        texto_fusao = FUSAO / concelho / f"{slugify(titulo)}.md"
        fotos, anexos = listar_media(slugify(titulo), RAIZ)
        saida.append(Espaco(
            titulo=titulo, concelho=CONCELHOS[concelho], seleccionado=bool(res.get("seleccionado")), selecao=selecao if res.get("seleccionado") else None,
            texto=(ler_fusao(texto_fusao) if texto_fusao.exists() else None) or "", freguesia=res.get("freguesia"),
            n_ficha=int(ficha["n_ficha"]) if ficha and ficha.get("n_ficha") else None,
            area_ha=area_em_ha(ficha["area_texto"]) if ficha and ficha.get("area_texto") else None,
            lat=coord[0] if coord else None, lon=coord[1] if coord else None,
            origem_coord=("ficha 2006–2008 (WGS84, 2 casas decimais)" if fonte_coord != "webnode" else "Webnode da campanha (WGS84, 2 casas decimais)") if coord else None,
            fotos=fotos, anexos=anexos,
            fontes=[ROTULO[f] for f in ("zip", "pdf", "webnode", "selecao") if f in reg["fontes"]],
        ))
    return saida


if __name__ == "__main__":
    fontes = _carregar()
    es = [e for c in CONCELHOS for e in espacos_do_concelho(c, fontes)]
    es = [e for e in es if e.texto]  # só publica o que tem texto revisto
    print(len(gerar(es, RAIZ)), "ficheiros;", len(es), "espaços com texto revisto")
