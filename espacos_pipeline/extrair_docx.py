"""Extracção das fichas de 2006–2008 (.docx; .doc via antiword) do zip e da pasta de projecto."""
import json
import re
import subprocess
import sys
from pathlib import Path

import docx

from espacos_pipeline.fontes import PROJECTO, SITE_ZIP
from espacos_pipeline.modelo import slugify

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "docs" / "fonte_campanha" / "extraido"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_TELEF = re.compile(
    r"(?<!\d)(?:\+351[ ]?)?(?:\d{9}|\d{3}[ .]\d{3}[ .]\d{3}|\d{2}[ .]\d{3}[ .]\d{2}[ .]\d{2})(?!\d)"
)
_COORD = re.compile(r"WGS84:?\s*(-?\d+[,.]\d+)\s*;\s*(-?\d+[,.]\d+)")
_SECCAO = re.compile(r"^\d\.\s")


def limpar_contactos(texto: str) -> tuple:
    """Remove e-mails e telefones; devolve (texto limpo, número de remoções)."""
    texto, n_mail = _EMAIL.subn("", texto)
    texto, n_tel = _TELEF.subn("", texto)
    return re.sub(r"[ \t]{2,}", " ", texto).strip(), n_mail + n_tel


def _linhas(tabela):
    for r in tabela.rows:
        vals = []
        for c in r.cells:
            t = c.text.strip()
            if t and t not in vals:
                vals.append(t)
        if vals:
            yield vals


def extrair_ficha(caminho: Path) -> dict:
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".doc":
        return _extrair_doc(caminho)
    d = docx.Document(caminho)
    campos, descricao, removidos = {}, {}, 0
    primeira = None
    for tabela in d.tables:
        for vals in _linhas(tabela):
            if primeira is None:
                primeira = vals[0]
            if len(vals) == 1 or _SECCAO.match(vals[0]):
                continue
            if len(vals) == 2:
                campos[vals[0]] = vals[1]
            else:
                chave, sub, valor = vals[0], vals[1], " ".join(vals[2:])
                limpo, n = limpar_contactos(valor)
                removidos += n
                if chave.startswith("Descri"):
                    descricao[sub] = limpo
                else:
                    campos[f"{chave} / {sub}"] = limpo
    for k in list(campos):
        campos[k], n = limpar_contactos(campos[k]) if k != "Espaço proposto por" else (campos[k], 0)
        removidos += n
    ficha = {
        "origem_ficheiro": str(caminho.relative_to(RAIZ)) if caminho.is_relative_to(RAIZ) else str(caminho),
        "titulo": campos.get("Nome do espaço") or primeira or caminho.stem,
        "n_ficha": _n_ficha(campos.get("Código", ""), caminho.name),
        "concelho": campos.get("Concelho"),
        "freguesia": campos.get("Freguesias") or campos.get("Freguesia"),
        "area_texto": campos.get("Área aproximada"),
        "tipologia": campos.get("Tipologia"),
        "proposto_por": campos.get("Espaço proposto por"),
        "descricao": descricao,
        "campos": campos,
        "contactos_removidos": removidos,
    }
    ficha["slug"] = slugify(ficha["titulo"])
    m = _COORD.search(campos.get("Outras referências", ""))
    if m:
        ficha["lat"], ficha["lon"] = (float(g.replace(",", ".")) for g in m.groups())
    return ficha


def _n_ficha(codigo: str, nome_ficheiro: str):
    for texto, padrao in ((codigo, r"ID\s*(\d+)"), (nome_ficheiro, r"Ficha_(\d+)")):
        m = re.search(padrao, texto)
        if m:
            return int(m.group(1))
    return None


def _extrair_doc(caminho: Path) -> dict:
    """.doc binário: texto bruto via antiword, a tratar na fusão editorial."""
    saida = subprocess.run(["antiword", "-w", "0", str(caminho)], capture_output=True, check=True)
    texto, n = limpar_contactos(saida.stdout.decode("utf-8", "replace"))
    titulo = re.sub(r"^Ficha_\d+_|_NQ$", "", caminho.stem).replace("_", " ").strip()
    return {
        "origem_ficheiro": str(caminho),
        "titulo": titulo,
        "slug": slugify(titulo),
        "n_ficha": _n_ficha("", caminho.name),
        "texto_bruto": texto,
        "contactos_removidos": n,
        "formato": "doc",
    }


def extrair_pasta(pasta: Path, concelho_de: callable) -> dict:
    """Mapa slug → ficha para todos os .doc/.docx sob `pasta` (duplicados por slug ficam em `_duplicados`)."""
    resultado, duplicados = {}, []
    for p in sorted(Path(pasta).rglob("*")):
        if p.suffix.lower() in (".doc", ".docx") and not p.name.startswith("~$") and "pagina_antiga" not in p.parts:
            f = extrair_ficha(p)
            if not f.get("concelho"):
                f["concelho"] = concelho_de(p)
            if f["slug"] in resultado:
                duplicados.append(f["origem_ficheiro"])
            else:
                resultado[f["slug"]] = f
    if duplicados:
        resultado["_duplicados"] = duplicados
    return resultado


if __name__ == "__main__":
    SAIDA.mkdir(parents=True, exist_ok=True)
    alvos = {
        "docx_projecto.json": (PROJECTO / "Espacos" / "Fichas", lambda p: p.parent.name),
        "docx_zip.json": (SITE_ZIP / "espacos" / "lista" / "fichas", lambda p: p.relative_to(SITE_ZIP / "espacos" / "lista" / "fichas").parts[0]),
    }
    for nome, (pasta, conc) in alvos.items():
        dados = extrair_pasta(pasta, conc)
        (SAIDA / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
        print(nome, len([k for k in dados if k != "_duplicados"]), "fichas", len(dados.get("_duplicados", [])), "duplicados")
