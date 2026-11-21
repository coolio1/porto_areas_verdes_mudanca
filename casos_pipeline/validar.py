"""Validação dos casos: esquema, concelho, excertos literais e fotos. `python -m casos_pipeline.validar`."""
import hashlib
import sys
from pathlib import Path

from casos_pipeline.concelho import dentro_do_porto
from casos_pipeline.modelo import (CRITERIOS, ESTADOS, GALERIAS, PAPEIS, RAIZ, TIPOS,
                                   excerto_em_texto, listar_casos)

FONTES = Path(r"C:\Users\quent\OneDrive\Claude\Fontes\Horrores")
MEDIA = RAIZ / "Horrores" / "media"
OBRIGATORIOS = ("titulo", "galeria", "tipo", "lat", "lon", "origem_coord", "ano", "estado",
                "contestacao", "criterio")


def _http(url) -> bool:
    return str(url).lower().startswith(("http://", "https://"))


def validar_caso(caso: dict, raiz_fontes: Path, raiz_media: Path = None) -> list:
    """Erros em PT-PT; lista vazia = válido. `raiz_media` (opcional) confere ficheiros e sha256 das fotos."""
    e = []
    for c in OBRIGATORIOS:
        if caso.get(c) in (None, ""):
            e.append(f"falta o campo «{c}»")
    for campo, validos in (("tipo", TIPOS), ("galeria", GALERIAS), ("estado", ESTADOS), ("criterio", CRITERIOS)):
        if caso.get(campo) not in (None, "") and caso[campo] not in validos:
            e.append(f"{campo} «{caso[campo]}» inválido (válidos: {', '.join(validos)})")
    if caso.get("titulo") and caso.get("title") != caso["titulo"]:
        e.append("falta «title» igual a «titulo» (o <title> da página e as pré-visualizações usam-no)")
    if "freguesia" in caso:
        e.append("«freguesia» não se escreve: deriva-se de lat/lon pela CAOP")
    if caso.get("criterio") == "editorial" and not caso.get("nota_editorial"):
        e.append("criterio «editorial» exige «nota_editorial»")
    if isinstance(caso.get("lat"), (int, float)) and isinstance(caso.get("lon"), (int, float)):
        if not dentro_do_porto(caso["lat"], caso["lon"]):
            e.append("lat/lon fora do concelho do Porto (CAOP 2025)")
    refs = caso.get("referencias") or []
    if not refs:
        e.append("sem referências: é preciso pelo menos 1 referência com excerto")
    for i, r in enumerate(refs, 1):
        if not r.get("url") or not r.get("excerto"):
            e.append(f"referência {i}: faltam «url» ou «excerto»")
            continue
        if not _http(r["url"]):
            e.append(f"referência {i}: url tem de começar por http:// ou https://")
        txt = Path(raiz_fontes) / caso.get("slug", "") / f"{i}.txt"
        if not txt.is_file():
            e.append(f"referência {i}: sem texto guardado em {txt}")
        elif not excerto_em_texto(r["excerto"], txt.read_text(encoding="utf-8")):
            e.append(f"referência {i}: excerto não encontrado no texto da fonte")
    for f in caso.get("fotos") or []:
        nome = f.get("ficheiro", "?")
        if f.get("papel") not in PAPEIS:
            e.append(f"foto {nome}: papel inválido")
        if not f.get("url"):
            e.append(f"foto {nome}: falta o url de origem")
        elif not _http(f["url"]):
            e.append(f"foto {nome}: url tem de começar por http:// ou https://")
        if raiz_media is not None:
            p = Path(raiz_media) / caso.get("slug", "") / nome
            if not p.is_file():
                e.append(f"foto {nome}: ficheiro em falta em {p}")
            elif hashlib.sha256(p.read_bytes()).hexdigest() != f.get("sha256"):
                e.append(f"foto {nome}: sha256 não confere")
    return e


def validar_todos(raiz: Path = RAIZ, raiz_fontes: Path = FONTES, raiz_media: Path = MEDIA) -> dict:
    """{slug: erros} só dos casos com erros."""
    out = {}
    for c in listar_casos(raiz):
        erros = validar_caso(c, raiz_fontes, raiz_media)
        if erros:
            out[c["slug"]] = erros
    return out


if __name__ == "__main__":
    resultado = validar_todos()
    for slug, erros in resultado.items():
        print(f"{slug}:", *erros, sep="\n  - ")
    print(f"{len(listar_casos())} casos, {len(resultado)} com erros")
    sys.exit(1 if resultado else 0)
