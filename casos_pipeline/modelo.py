"""Esquema e leitura dos casos: `_casos/<slug>.md` (front matter YAML + descrição)."""
import re
import unicodedata
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]

TIPOS = ("arvores", "demolicao", "patrimonio_alterado", "lojas_historicas")
GALERIAS = ("horrores", "sucessos")
ESTADOS = ("demolido", "alterado", "abatido", "revertido", "outro")
CRITERIOS = ("documental", "lista", "editorial")
PAPEIS = ("antes", "depois", "outra")


class _Carregador(yaml.SafeLoader):
    """YAML sem datas automáticas: `data: 2019-03-01` fica texto (serializa-se em JSON sem tratamento)."""


_Carregador.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:timestamp"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}

_TIPOGRAFIA = str.maketrans({"«": '"', "»": '"', "“": '"', "”": '"', "„": '"', "‘": "'", "’": "'",
                             "–": "-", "—": "-", "−": "-"})


def normalizar(t: str) -> str:
    """Minúsculas, aspas e travessões tipográficos → ASCII, espaços colapsados (para comparar excertos)."""
    t = unicodedata.normalize("NFKC", t).translate(_TIPOGRAFIA).lower()
    return re.sub(r"\s+", " ", t).strip()


def excerto_em_texto(excerto: str, texto: str) -> bool:
    e = normalizar(excerto)
    return bool(e) and e in normalizar(texto)


def ler_caso(caminho: Path) -> dict:
    """Front matter + `corpo` (descrição), `slug` (nome do ficheiro) e `caminho`."""
    partes = Path(caminho).read_text(encoding="utf-8").split("---", 2)
    if len(partes) < 3:
        raise ValueError(f"{caminho}: sem front matter")
    caso = yaml.load(partes[1], Loader=_Carregador) or {}
    caso.update(corpo=partes[2].strip(), slug=Path(caminho).stem, caminho=Path(caminho))
    return caso


def listar_casos(raiz: Path = RAIZ) -> list:
    """Só `_casos/*.md` (os rascunhos vivem noutra pasta e nunca entram)."""
    return [ler_caso(p) for p in sorted((Path(raiz) / "_casos").glob("*.md"))]
