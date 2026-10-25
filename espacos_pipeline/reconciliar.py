"""Reconciliação das fontes por ID de ficha: presença, divergências (registadas, nunca resolvidas)."""
import difflib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from espacos_pipeline.modelo import slugify

RAIZ = Path(__file__).resolve().parents[1]
EXTRAIDO = RAIZ / "docs" / "fonte_campanha" / "extraido"
ORDEM_FONTES = ("zip", "projecto", "pdf", "webnode", "selecao")
TOLERANCIA_COORD = 0.011  # as fontes têm 2 casas decimais

_CONCELHOS = (
    (r"^gaia|vila nova de gaia", "vila-nova-de-gaia"),
    (r"vila[ _]?(do )?conde", "vila-do-conde"),
    (r"^p.?voa", "povoa-de-varzim"),
    (r"^porto", "porto"), (r"^gondomar", "gondomar"), (r"^valongo", "valongo"),
    (r"^maia", "maia"), (r"^matosinhos", "matosinhos"), (r"^espinho", "espinho"),
)


def _sem_acentos(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def norm_concelho(nome) -> str:
    base = _sem_acentos(nome or "")
    for padrao, canonico in _CONCELHOS:
        if re.search(padrao, base):
            return canonico
    return slugify(base)


@dataclass
class Relatorio:
    registos: list = field(default_factory=list)
    divergencias: list = field(default_factory=list)
    so_numa_fonte: list = field(default_factory=list)
    webnode_sem_id: list = field(default_factory=list)


def _similaridade(a: str, b: str) -> float:
    ta, tb = slugify(a), slugify(b)
    ordenados = lambda s: " ".join(sorted(s.split("-")))
    pontos = [difflib.SequenceMatcher(None, ta, tb).ratio(), difflib.SequenceMatcher(None, ordenados(ta), ordenados(tb)).ratio()]
    if min(len(ta), len(tb)) >= 6 and (ta in tb or tb in ta):
        pontos.append(0.85)
    return max(pontos)


def _entradas(fontes: dict, fonte: str, concelho_webnode: str):
    """Entradas normalizadas de uma fonte: dicts com id, titulo, concelho, freguesia, coordenadas, seleccionado."""
    def coords(d):
        return (d["lat"], d["lon"]) if d.get("lat") is not None and d.get("lon") is not None else None

    if fonte in ("zip", "projecto"):
        for chave, f in fontes.get(fonte, {}).items():
            if chave != "_duplicados" and isinstance(f, dict):
                yield {"id": f.get("n_ficha"), "titulo": f.get("titulo"), "concelho": norm_concelho(f.get("concelho")) if f.get("concelho") else None,
                       "freguesia": f.get("freguesia"), "coordenadas": coords(f), "origem": f}
    elif fonte == "pdf":
        for f in fontes.get("pdf", {}).values():
            yield {"id": f["id"], "titulo": f.get("titulo"), "concelho": norm_concelho(f["concelho"]) if f.get("concelho") else None,
                   "seleccionado": f.get("seleccionado"), "origem": f}
    elif fonte == "selecao":
        for s in fontes.get("selecao", []):
            yield {"id": s.get("id"), "titulo": s.get("nome"), "concelho": norm_concelho(s.get("concelho")) if s.get("concelho") else None,
                   "seleccionado": s.get("selecao") is not None, "origem": s}
    elif fonte == "webnode":
        for w in fontes.get("webnode", []):
            yield {"id": None, "titulo": w["titulo"], "concelho": concelho_webnode, "freguesia": w.get("freguesia"),
                   "coordenadas": coords(w), "seleccionado": w.get("seleccionado"), "origem": w}


def _novo_registo() -> dict:
    return {"fontes": [], "id": {}, "titulo": {}, "concelho": {}, "freguesia": {}, "coordenadas": {}, "seleccionado": {}}


def _juntar(reg: dict, fonte: str, e: dict):
    reg["fontes"].append(fonte)
    for campo in ("id", "titulo", "concelho", "freguesia", "coordenadas", "seleccionado"):
        if e.get(campo) not in (None, ""):
            reg[campo][fonte] = e[campo]


def _pontuar(reg: dict, e: dict) -> float:
    base = max((_similaridade(e["titulo"], t) for t in reg["titulo"].values()), default=0.0)
    mesmo_id = e["id"] is not None and e["id"] in set(reg["id"].values())
    outro_concelho = e["concelho"] and reg["concelho"] and e["concelho"] not in set(reg["concelho"].values())
    if outro_concelho and not (mesmo_id and base >= 0.9):  # espaços a cavalo entre concelhos (ex. Rio Ferreira)
        return 0.0
    return min(1.0, base + 0.15) if mesmo_id else base


LIMIAR = 0.6


def reconciliar(fontes: dict, concelho_webnode: str = "porto") -> Relatorio:
    rel = Relatorio()
    for fonte in ORDEM_FONTES:
        entradas = list(_entradas(fontes, fonte, concelho_webnode))
        pares = sorted(((_pontuar(r, e), i, j) for i, r in enumerate(rel.registos) for j, e in enumerate(entradas)), reverse=True)
        usados_r, usados_e = set(), set()
        for pontos, i, j in pares:
            if pontos >= LIMIAR and i not in usados_r and j not in usados_e:
                _juntar(rel.registos[i], fonte, entradas[j])
                usados_r.add(i)
                usados_e.add(j)
        for j, e in enumerate(entradas):
            if j in usados_e:
                continue
            if fonte == "webnode":
                rel.webnode_sem_id.append(e["origem"])
            else:
                reg = _novo_registo()
                _juntar(reg, fonte, e)
                rel.registos.append(reg)
    for reg in rel.registos:
        if len(reg["fontes"]) == 1:
            rel.so_numa_fonte.append({"fonte": reg["fontes"][0], "titulo": next(iter(reg["titulo"].values()), None), "id": next(iter(reg["id"].values()), None)})
        _comparar(rel, reg)
    return rel


def _comparar(rel: Relatorio, r: dict):
    nome = next(iter(r["titulo"].values()), None)

    def regista(campo, valores):
        rel.divergencias.append({"titulo": nome, "campo": campo, "valores": valores})

    if len(set(r["id"].values())) > 1:
        regista("id", dict(r["id"]))
    fregs = r["freguesia"]
    if len(fregs) > 1:
        normas = [_sem_acentos(v) for v in fregs.values()]
        a, *resto = normas
        if any(a not in x and x not in a for x in resto):
            regista("freguesia", dict(fregs))
    cs = r["coordenadas"]
    if len(cs) > 1:
        lat0, lon0 = next(iter(cs.values()))
        if any(abs(lat - lat0) > TOLERANCIA_COORD or abs(lon - lon0) > TOLERANCIA_COORD for lat, lon in cs.values()):
            regista("coordenadas", {k: list(v) for k, v in cs.items()})
    if len(set(r["seleccionado"].values())) > 1:
        regista("seleccionado", dict(r["seleccionado"]))
    if len(set(r["concelho"].values())) > 1:
        regista("concelho", dict(r["concelho"]))


def _mesmo(campo: str, a, b) -> bool:
    if campo == "coordenadas":
        return abs(a[0] - b[0]) <= TOLERANCIA_COORD and abs(a[1] - b[1]) <= TOLERANCIA_COORD
    if campo == "freguesia":
        x, y = _sem_acentos(a), _sem_acentos(b)
        return x in y or y in x
    return a == b


def _escolher(campo: str, valores: dict):
    """Regra: prevalece o valor que 2+ fontes concordam; o Webnode só desempata em último lugar.
    Devolve (valor, regra) — regra é None quando não há divergência."""
    grupos = []  # [valor, [fontes]]
    for fonte, v in valores.items():
        for g in grupos:
            if _mesmo(campo, g[0], v):
                g[1].append(fonte)
                break
        else:
            grupos.append([v, [fonte]])
    if len(grupos) == 1:
        return grupos[0][0], None
    melhor = max(grupos, key=lambda g: (len(g[1]), any(f != "webnode" for f in g[1])))
    if len(melhor[1]) >= 2 and sum(len(g[1]) == len(melhor[1]) for g in grupos) == 1:
        return melhor[0], "2+ fontes"
    return melhor[0], "empate: fonte não-Webnode"


def resolver(rel: Relatorio) -> list:
    """Acrescenta a cada registo `resolvido` (valor final por campo) e `decisoes` (só onde havia divergência)."""
    for reg in rel.registos:
        reg["resolvido"], reg["decisoes"] = {}, []
        for campo in ("freguesia", "coordenadas", "seleccionado"):
            if not reg[campo]:
                continue
            valor, regra = _escolher(campo, reg[campo])
            reg["resolvido"][campo] = list(valor) if campo == "coordenadas" else valor
            if regra:
                reg["decisoes"].append({"campo": campo, "regra": regra, "valores": dict(reg[campo]), "escolhido": reg["resolvido"][campo]})
    return rel.registos


def escrever_md(rel: Relatorio, destino: Path):
    linhas = ["# Reconciliação das fontes", "", f"- Espaços (registos): {len(rel.registos)}",
              f"- Só numa fonte: {len(rel.so_numa_fonte)}", f"- Webnode sem ID: {len(rel.webnode_sem_id)}",
              f"- Divergências: {len(rel.divergencias)}", ""]
    if rel.so_numa_fonte:
        linhas += ["## Só numa fonte", ""] + [f"- {x['titulo']} (ID {x['id']}, só em {x['fonte']})" for x in rel.so_numa_fonte] + [""]
    if rel.webnode_sem_id:
        linhas += ["## Webnode sem correspondência", ""] + [f"- {w['titulo']}" for w in rel.webnode_sem_id] + [""]
    linhas += ["## Divergências", "", "| Espaço | Campo | Valores por fonte |", "|---|---|---|"]
    for d in rel.divergencias:
        linhas.append(f"| {d['titulo']} | {d['campo']} | {json.dumps(d['valores'], ensure_ascii=False)} |")
    decisoes = [(r, d) for r in rel.registos for d in r.get("decisoes", [])]
    if decisoes:
        linhas += ["", "## Decisões (regra: prevalece o que 2+ fontes concordam)", "", "| Espaço | Campo | Regra | Escolhido | Valores por fonte |", "|---|---|---|---|---|"]
        for r, d in decisoes:
            nome = next(iter(r["titulo"].values()), None)
            linhas.append(f"| {nome} | {d['campo']} | {d['regra']} | {json.dumps(d['escolhido'], ensure_ascii=False)} | {json.dumps(d['valores'], ensure_ascii=False)} |")
    Path(destino).write_text("\n".join(linhas) + "\n", encoding="utf-8")


def _carregar() -> dict:
    ler = lambda n: json.loads((EXTRAIDO / n).read_text(encoding="utf-8"))
    return {
        "zip": ler("docx_zip.json"), "projecto": ler("docx_projecto.json"),
        "pdf": ler("pdf2016.json")["fichas"], "webnode": ler("webnode_porto.json")["espacos"], "selecao": ler("selecao2009.json"),
    }


if __name__ == "__main__":
    rel = reconciliar(_carregar())
    resolver(rel)
    destino = RAIZ / "docs" / "fonte_campanha" / "reconciliacao.md"
    escrever_md(rel, destino)
    print(f"{len(rel.registos)} registos; só numa fonte {len(rel.so_numa_fonte)}; webnode sem ID {len(rel.webnode_sem_id)}; divergências {len(rel.divergencias)} -> {destino}")
