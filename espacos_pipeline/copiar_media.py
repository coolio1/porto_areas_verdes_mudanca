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


def _nome_livre(destino: Path, nome: str) -> str:
    p = Path(nome)
    n, cand = 2, nome
    while (destino / cand).exists():
        cand = f"{p.stem}-{n}{p.suffix}"
        n += 1
    return cand


def copiar_media(slug: str, origens: list, destino: Path, max_lado: int = 1400) -> list:
    """Copia fotos (reduzidas a max_lado, JPEG q=82) e PDFs (inalterados) para `destino`.

    `origens` aceita ficheiros ou pastas (percorridas; ignoram-se miniaturas e páginas antigas).
    Devolve caminhos relativos a `destino.parent`, ex. 'slug/01.jpg'. Duplicados (mesmo conteúdo)
    são copiados uma só vez; nomes iguais com conteúdo diferente ganham sufixo -2, -3.
    """
    destino = Path(destino)
    vistos, saida = set(), []
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
            nome = _nome_livre(destino, p.name)
            shutil.copyfile(p, destino / nome)
        else:
            nome = _nome_livre(destino, p.stem + ".jpg")
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


# Pasta de ficha do site original (lista/ e listaf/) -> slug. 23 espaços do Porto.
PORTO = {
    "aldoar/41": "pinhal-de-aldoar", "aldoar/48": "quinta-da-familia-carneiro",
    "campanha/40": "parque-oriental", "campanha/85": "monte-do-forte",
    "campanha/87": "morro-das-mimosas", "campanha/90": "antiga-quinta-do-eng-cunha-lima",
    "cedofeita/46": "quinta-da-bouca", "cedofeita/52": "quinta-de-santo-antonio-de-aguas-ferreas",
    "foz/55": "quinta-do-monte", "lordelo_ouro/68": "ribeira-da-granja",
    "massarelos/05": "caminhos-do-romantico",
    "massarelos/39": "parque-e-cemiterio-da-igreja-de-saint-james-cemiterio-ingles",
    "nevogilde/26": "villa-monte-crasto",
    "nevogilde/47": "quinta-da-familia-botelho-de-lacerda-lobo-vilares",
    "nevogilde/91": "antigos-terrenos-agricolas-em-aldoar-e-nevogilde",
    "paranhos/18": "jardins-do-hospital-conde-de-ferreira",
    "paranhos/63": "quinta-dos-frades-menores-capuchinhos",
    "ramalde/07": "casa-da-familia-robinson", "ramalde/15": "jardim-de-espaco-canal",
    "ramalde/17": "jardim-junto-a-vci", "ramalde/43": "pinheiros-mansos-e-logradouros-adjacentes",
    "ramalde/44": "quinta-antiga-perto-da-prelada", "ramalde/51": "quinta-da-prelada",
}


# PDFs com dados pessoais (telefones, assinaturas): não se publicam.
EXCLUIR_PESSOAIS = {
    "2003-12-15-Assinaturas_para_defesa_do_Parque_Oriental.pdf",
    "2003-11-05-Manifesto_em_defesa_do_Parque_Oriental.pdf",
    "Parecer_sobre_a_Estrategia_de_Valorizacao_do_Vale_da_Ribeira_Granja.pdf",
}


def copiar_porto(raiz: Path) -> dict:
    """Copia as mídias do Porto para <raiz>/50espacos/media/<slug>/. Devolve {slug: [caminhos]}."""
    base = raiz / "docs" / "fonte_campanha" / "site_zip" / "espacos"
    res = {}
    for pasta, slug in PORTO.items():
        origens = [base / v / "fichas" / "porto" / pasta for v in ("lista", "listaf")]
        ficheiros = [f for o in origens if o.is_dir() for f in sorted(o.rglob("*"))
                     if f.is_file() and f.name not in EXCLUIR_PESSOAIS
                     and not (IGNORAR_PASTAS & set(x.name for x in f.relative_to(o).parents))]
        res[slug] = copiar_media(slug, ficheiros, raiz / "50espacos" / "media" / slug)
    return res


if __name__ == "__main__":
    import json
    r = copiar_porto(Path(__file__).resolve().parent.parent)
    print(json.dumps({k: len(v) for k, v in r.items()}, indent=1), sum(map(len, r.values())))
