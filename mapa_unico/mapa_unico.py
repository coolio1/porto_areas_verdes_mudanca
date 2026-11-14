"""Gera mapa_unico.html (página única com 4 temas) e os ficheiros de dados por tema.

Fontes: src/ (CSS, JS do núcleo e dos temas, modelo HTML) e layers/ (PNG já calculados
pelos pipelines de cada tema). Nunca editar o HTML gerado à mão.

Uso (a partir de qualquer pasta):  python mapa_unico/mapa_unico.py
"""

import base64
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(RAIZ))
from carto import aplicar_chave
from nav import get_css_link, get_nav, get_rodape

SRC = AQUI / "src"
DADOS = AQUI / "dados"
LAYERS = RAIZ / "layers"
PAGINA = "mapa_unico/mapa_unico.html"

# Temas na ordem dos separadores (um ficheiro src/tema_<id>.js cada)
TEMAS = ["hoje", "acessibilidade", "historico", "privado"]

# Ficheiros de dados: nome -> {chave JS: ficheiro PNG}
PNG_DADOS = {
    "contexto": {
        "municipios": LAYERS / "municipios.png",
        "ghspop": LAYERS / "ghspop.png",
    },
    "hoje": {
        k: LAYERS / f"{k}.png"
        for k in (
            "uso_arvores",
            "uso_solo",
            "uso_edificado",
            "arvores_edificado",
            "arvores_solo",
            "solo_edificado",
            "solo_arvores",
        )
    },
    "privado": {
        "interior_subsistente": LAYERS / "interior_subsistente_corrigido.png",
        "interior_perdido": LAYERS / "interior_perdido.png",
        "centro_alargado": LAYERS / "centro_alargado.png",
    },
}


def _b64(p: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def _escrever(nome: str, obj: dict) -> None:
    # compacto; ensure_ascii=False mantém os acentos legíveis nos GeoJSON
    js = f"MU.DADOS[{json.dumps(nome)}] = {json.dumps(obj, separators=(',', ':'), ensure_ascii=False)};\n"
    (DADOS / f"{nome}.js").write_text(js, encoding="utf-8")
    print(f"dados/{nome}.js  {len(js) // 1024} KB")


def dados_acessibilidade() -> dict:
    """Imagens pré-coloridas, GeoJSON (parques e candidatos) e percentagens das Propostas."""
    acc = RAIZ / "acessibilidade"
    imgs = {
        "acc": acc / "layers" / "acessibilidade_2sfca.png",
        "acc_sim": acc / "layers" / "acessibilidade_2sfca_sim.png",
        "prox": acc / "layers" / "proximidade_300m.png",
        "prox_sim": acc / "layers" / "proximidade_simulada.png",
        "baixa": acc / "layers" / "baixa_densidade.png",
        "pago": acc / "layers" / "verde_pago_colored.png",
        "privado": LAYERS
        / "interior_subsistente_colored.png",  # todas as áreas (antes da correcção)
    }
    return {
        "imgs": {k: _b64(p) for k, p in imgs.items()},
        "parques": json.loads(
            (acc / "parques_porto.geojson").read_text(encoding="utf-8")
        ),
        "candidatos": json.loads(
            (acc / "candidatos_conversao.geojson").read_text(encoding="utf-8")
        ),
        "meta": json.loads(
            (acc / "layers" / "conversao_metadata.json").read_text(encoding="utf-8")
        ),
    }


EPOCAS = ["1985-90", "1995-00", "2001-05", "2016-17", "2023-24"]


def _png_1bit(p: Path) -> bytes:
    """PNG RGBA de uma só cor (alfa 0/200) -> PNG de paleta a 1 bit com tRNS (metade do peso)."""
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(p).convert("RGBA")
    import numpy as np

    a = np.array(im)
    m = a[..., 3] > 0
    r, g, b, al = (int(v) for v in a[m][0])
    assert (a[m] == [r, g, b, al]).all(), f"{p.name}: mais de uma cor"
    out = Image.fromarray(m.astype(np.uint8), mode="P")
    out.putpalette([0, 0, 0, r, g, b])
    import io

    buf = io.BytesIO()
    out.save(buf, format="PNG", bits=1, optimize=True, transparency=bytes([0, al]))
    return buf.getvalue()


def dados_historico() -> dict:
    """1947 (limpa, 1 bit), épocas Landsat (sem NDVI), perda/ganho, Land cover 1979 (Filipa Guilherme) e percentagens por época."""
    import cobertura_1979 as c79
    from historico_numeros import percentagens

    hist = RAIZ / "layers_historico"
    d: dict = {}
    for k in ("uso_1947_vegetacao", "uso_1947_edificado"):
        d[k] = (
            "data:image/png;base64,"
            + base64.b64encode(
                _png_1bit(RAIZ / "1947" / "layers" / f"{k}.png")
            ).decode()
        )
    for e in EPOCAS:
        for pre in ("veg", "edif"):
            d[f"{pre}_{e}"] = _b64(hist / f"{pre}_{e}.png")
    for k in ("veg_perda", "veg_ganho"):
        d[k] = _b64(hist / f"{k}.png")
    g = c79.carregar()
    mveg = c79.mascara_png(g, ["TRS", "HER"], c79.COR_VEG)
    medif = c79.mascara_png(g, ["ABE"], c79.COR_EDIF)
    d["veg_1979"] = "data:image/png;base64," + base64.b64encode(mveg).decode()
    d["edif_1979"] = "data:image/png;base64," + base64.b64encode(medif).decode()
    d["cobertura_1979"] = c79.geojson(g)
    d["cobertura_1979_ha"] = {
        k: round(float(v), 1) for k, v in g.groupby("LC_1979_ab")["ha"].sum().items()
    }
    d["numeros"] = percentagens(RAIZ)
    return d


def escrever_dados() -> None:
    DADOS.mkdir(exist_ok=True)
    for nome, imgs in PNG_DADOS.items():
        _escrever(nome, {k: _b64(p) for k, p in imgs.items()})
    _escrever("acessibilidade", dados_acessibilidade())
    _escrever("historico", dados_historico())


def escrever_html() -> None:
    js = (SRC / "core.js").read_text(encoding="utf-8")
    for t in TEMAS:
        js += "\n" + (SRC / f"tema_{t}.js").read_text(encoding="utf-8")
    html = (SRC / "template.html").read_text(encoding="utf-8")
    html = (
        html.replace("/*CSS*/", (SRC / "estilo.css").read_text(encoding="utf-8"))
        .replace("<!--CSS-->", get_css_link(depth=1))
        .replace("<!--NAV-->", get_nav(PAGINA, depth=1))
        .replace("<!--RODAPE-->", get_rodape(PAGINA, depth=1, modo="mapa"))
        .replace("/*JS*/", js)
    )
    saida = AQUI / "mapa_unico.html"
    saida.write_text(aplicar_chave(html), encoding="utf-8")
    print(f"mapa_unico.html  {saida.stat().st_size // 1024} KB")


if __name__ == "__main__":
    # --html: só o HTML (os dados do Histórico demoram ~2 min por causa das máscaras de 1947)
    if "--html" not in sys.argv:
        escrever_dados()
    escrever_html()
