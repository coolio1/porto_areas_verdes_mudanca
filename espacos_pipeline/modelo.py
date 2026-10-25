"""Modelo de dados de um espaço da campanha e validação antes de publicar."""
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

SELECOES = ("2009-04", "posterior")
ESTADOS = ("por verificar", "preservado", "parcialmente construído", "destruído", "ameaçado")
# Nome público de cada concelho da campanha (chave = slug canónico de `reconciliar.norm_concelho`).
CONCELHOS = {
    "porto": "Porto", "vila-nova-de-gaia": "Vila Nova de Gaia", "gondomar": "Gondomar", "maia": "Maia", "matosinhos": "Matosinhos",
    "vila-do-conde": "Vila do Conde", "espinho": "Espinho", "valongo": "Valongo", "povoa-de-varzim": "Póvoa de Varzim",
}

# Caixa envolvente da AMP (graus WGS84): apanha o sinal de longitude em falta e gralhas grosseiras.
BBOX_AMP = {"lat": (40.8, 41.5), "lon": (-8.9, -8.3)}

_CONTACTO = re.compile(r"@|\+351|\b\d{9}\b|\b\d{3}[ .]\d{3}[ .]\d{3}\b")


@dataclass
class Espaco:
    titulo: str
    concelho: str
    seleccionado: bool = False
    texto: str = ""
    freguesia: Optional[str] = None
    n_ficha: Optional[int] = None
    selecao: Optional[str] = None  # "2009-04" (lista final de Abril de 2009) ou "posterior" (acrescentado depois)
    proponente: Optional[str] = None
    area_ha: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    origem_coord: Optional[str] = None
    estado_actual: str = "por verificar"
    data_verificacao: Optional[str] = None
    fontes: list = field(default_factory=list)
    fotos: list = field(default_factory=list)
    anexos: list = field(default_factory=list)

    @property
    def slug(self) -> str:
        return slugify(self.titulo)


def slugify(nome: str) -> str:
    sem_acentos = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acentos.lower()).strip("-")


def validar(e: Espaco) -> list:
    erros = []
    if e.seleccionado and e.selecao not in SELECOES:
        erros.append(f"{e.titulo}: seleccionado sem selecao válida")
    if not e.seleccionado and e.selecao is not None:
        erros.append(f"{e.titulo}: selecao em espaço não seleccionado")
    if (e.lat is None) != (e.lon is None) or (e.lat == 0 and e.lon == 0):
        erros.append(f"{e.titulo}: coordenadas incompletas ou a zero")
    elif e.lat is not None and not e.origem_coord:
        erros.append(f"{e.titulo}: coordenadas sem origem_coord")
    if e.lat is not None and e.lon is not None and not (
        BBOX_AMP["lat"][0] <= e.lat <= BBOX_AMP["lat"][1] and BBOX_AMP["lon"][0] <= e.lon <= BBOX_AMP["lon"][1]
    ):
        erros.append(f"{e.titulo}: coordenadas fora da AMP ({e.lat}, {e.lon})")
    if e.estado_actual not in ESTADOS:
        erros.append(f"{e.titulo}: estado_actual inválido ({e.estado_actual})")
    if _CONTACTO.search(e.texto):
        erros.append(f"{e.titulo}: o texto parece conter contacto pessoal")
    return erros


def validar_lote(espacos: list) -> list:
    erros = [m for e in espacos for m in validar(e)]
    slugs = Counter((slugify(e.concelho), e.slug) for e in espacos)
    erros += [f"slug repetido: {c}/{s}" for (c, s), n in slugs.items() if n > 1]
    return erros
