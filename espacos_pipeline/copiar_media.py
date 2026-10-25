"""Cópia de fotos e anexos de um espaço para 50espacos/media/<slug>/."""
import hashlib
import shutil
from pathlib import Path

from PIL import Image

FOTOS = {".jpg", ".jpeg", ".png", ".gif"}
ANEXOS = {".pdf"}
IGNORADAS = {".doc", ".docx", ".mno", ".html", ".htm"}
IGNORAR_PASTAS = {"peq", "slide", "ficha_html", "pagina_antiga"}


def _ficheiros(origens):
    for o in map(Path, origens):
        if o.is_dir():
            for p in sorted(o.rglob("*")):
                if p.is_file() and not (IGNORAR_PASTAS & set(x.name for x in p.relative_to(o).parents)) \
                        and not (IGNORAR_PASTAS & {p.parent.name}):
                    yield p
        elif o.is_file() and o.parent.name not in IGNORAR_PASTAS:
            yield o


def _nome_livre(usados: set, nome: str) -> str:
    p = Path(nome)
    n, cand = 2, nome
    while cand in usados:
        cand = f"{p.stem}-{n}{p.suffix}"
        n += 1
    usados.add(cand)
    return cand


def copiar_media(slug: str, origens: list, destino: Path, max_lado: int = 1400) -> list:
    """Copia fotos (reduzidas a max_lado, JPEG q=82) e PDFs (inalterados) para `destino`.

    `origens` aceita ficheiros ou pastas (percorridas; ignoram-se miniaturas e páginas antigas).
    Devolve caminhos relativos a `destino.parent`, ex. 'slug/01.jpg'. Duplicados (mesmo conteúdo)
    são copiados uma só vez; nomes iguais com conteúdo diferente ganham sufixo -2, -3.
    Idempotente: voltar a correr sobrescreve os mesmos nomes (não cria -2 sobre cópias anteriores).
    """
    destino = Path(destino)
    vistos, usados, saida = set(), set(), []
    for p in _ficheiros(origens):
        ext = p.suffix.lower()
        if ext in IGNORADAS or p.name.lower() == "thumbs.db" or ext not in FOTOS | ANEXOS:
            continue
        h = hashlib.sha256(p.read_bytes()).digest()
        if h in vistos:
            continue
        vistos.add(h)
        destino.mkdir(parents=True, exist_ok=True)
        if ext in ANEXOS:
            nome = _nome_livre(usados, p.name)
            shutil.copyfile(p, destino / nome)
        else:
            nome = _nome_livre(usados, p.stem + ".jpg")
            with Image.open(p) as im:
                if max(im.size) > max_lado:
                    im = im.convert("RGB")
                    im.thumbnail((max_lado, max_lado))
                    im.save(destino / nome, "JPEG", quality=82)
                elif ext in {".jpg", ".jpeg"}:
                    shutil.copyfile(p, destino / nome)
                else:
                    im.convert("RGB").save(destino / nome, "JPEG", quality=82)
        saida.append(f"{slug}/{nome}")
    return saida


# Pasta de concelho do site original (lista/ e listaf/) -> slug canónico do concelho.
PASTAS_CONCELHO = {
    "espinho": "espinho", "gaia": "vila-nova-de-gaia", "gondomar": "gondomar", "maia": "maia", "matosinhos": "matosinhos",
    "porto": "porto", "povoa": "povoa-de-varzim", "valongo": "valongo", "vila_conde": "vila-do-conde",
}


def atribuir_pastas(reivindicadas: dict, sem_pasta: dict, existentes: list) -> dict:
    """{slug: (pasta_concelho, pasta_freguesia, nn)}: as `reivindicadas` (pela ficha .docx) mais, para cada espaço
    de `sem_pasta` ({slug: (concelho, freguesia)}), a única pasta livre desse concelho cuja freguesia lhe corresponde."""
    from espacos_pipeline.modelo import slugify

    res = dict(reivindicadas)
    livres = [x for x in existentes if x not in set(res.values())]
    for slug, (concelho, freguesia) in sem_pasta.items():
        cand = [x for x in livres if PASTAS_CONCELHO.get(x[0]) == concelho and slugify(x[1].replace("_", " ")) in slugify(freguesia or "")]
        if len(cand) != 1:
            raise ValueError(f"{slug}: {len(cand)} pastas candidatas em {concelho}/{freguesia}")
        res[slug] = cand[0]
        livres.remove(cand[0])
    return res


# PDFs com dados pessoais (telefones, assinaturas): não se publicam.
EXCLUIR_PESSOAIS = {
    "2003-12-15-Assinaturas_para_defesa_do_Parque_Oriental.pdf",
    "2003-11-05-Manifesto_em_defesa_do_Parque_Oriental.pdf",
    "Parecer_sobre_a_Estrategia_de_Valorizacao_do_Vale_da_Ribeira_Granja.pdf",
    "Quinta_Marques_Gomes.pdf",  # telemóvel e e-mail pessoais
}


def pastas_dos_espacos(raiz: Path) -> dict:
    """{slug: (pasta_concelho, pasta_freguesia, nn)} para os 111 espaços, a partir da ficha .docx de cada um."""
    import re

    from espacos_pipeline.modelo import slugify
    from espacos_pipeline.reconciliar import _carregar, concelho_do_registo, reconciliar, resolver

    fontes = _carregar()
    rel = reconciliar(fontes)
    resolver(rel)
    reiv, sem = {}, {}
    for reg in rel.registos:
        t = reg["titulo"].get("webnode") or reg["titulo"].get("pdf") or next(iter(reg["titulo"].values()))
        pasta = None
        for fonte in ("zip", "projecto"):
            ficha = next((x for k, x in fontes[fonte].items() if k != "_duplicados" and isinstance(x, dict) and x.get("titulo") == reg["titulo"].get(fonte)), None)
            m = ficha and re.search(r"site_zip[\\/]espacos[\\/]lista[\\/]fichas[\\/]([^\\/]+)[\\/]([^\\/]+)[\\/]([^\\/]+)", ficha["origem_ficheiro"])
            if m:
                pasta = m.groups()
                break
        if pasta:
            reiv[slugify(t)] = pasta
        else:
            sem[slugify(t)] = (concelho_do_registo(reg), reg["resolvido"].get("freguesia"))
    base = raiz / "docs" / "fonte_campanha" / "site_zip" / "espacos" / "lista" / "fichas"
    existentes = [(c.name, f.name, n.name) for c in base.iterdir() if c.name in PASTAS_CONCELHO for f in c.iterdir() if f.is_dir() for n in f.iterdir() if n.is_dir()]
    return atribuir_pastas(reiv, sem, existentes)


def copiar_todos(raiz: Path) -> dict:
    """Copia as mídias de todos os espaços para <raiz>/50espacos/media/<slug>/. Devolve {slug: [caminhos]}."""
    base = raiz / "docs" / "fonte_campanha" / "site_zip" / "espacos"
    res = {}
    for slug, (concelho, freguesia, nn) in pastas_dos_espacos(raiz).items():
        origens = [base / v / "fichas" / concelho / freguesia / nn for v in ("lista", "listaf")]
        ficheiros = [f for o in origens if o.is_dir() for f in sorted(o.rglob("*"))
                     if f.is_file() and f.name not in EXCLUIR_PESSOAIS
                     and not (IGNORAR_PASTAS & set(x.name for x in f.relative_to(o).parents))]
        res[slug] = copiar_media(slug, ficheiros, raiz / "50espacos" / "media" / slug)
    return res


if __name__ == "__main__":
    import json
    r = copiar_todos(Path(__file__).resolve().parent.parent)
    print(len(r), "espaços;", sum(map(len, r.values())), "ficheiros;", "sem ficheiros:", [k for k, v in r.items() if not v])
