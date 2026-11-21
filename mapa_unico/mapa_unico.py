"""Gera mapa_unico.html (página única com 5 temas) e os ficheiros de dados por tema.

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
from nav import get_nav

SRC = AQUI / "src"
DADOS = AQUI / "dados"
LAYERS = RAIZ / "layers"
PAGINA = "mapa_unico/mapa_unico.html"

# Temas na ordem dos separadores (um ficheiro src/tema_<id>.js cada); o primeiro abre sem hash
TEMAS = ["acessibilidade", "regra", "hoje", "historico", "privado"]
# Horrores e sucessos: página própria (casos/index.html), gerada do mesmo código só com o tema `casos`
PAGINA_CASOS = "casos/"

ACC_LAYERS = RAIZ / "acessibilidade" / "layers"

# Ficheiros de dados: nome -> {chave JS: ficheiro PNG}
# (contexto: comum a todos os temas; o resto do contexto — água, fora do concelho, parques,
#  hectares — junta-se em dados_contexto())
PNG_DADOS = {
    "contexto": {
        "municipios": LAYERS / "municipios.png",
        "ghspop": LAYERS / "ghspop.png",
        "pago": ACC_LAYERS / "verde_pago_colored.png",
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


# Paleta das categorias de acessibilidade no mapa (maquete «Carta» V2b, validada para daltónicos):
# as imagens do pipeline (acessibilidade/layers/) saem com as cores antigas e são recoloridas
# aqui, cor exacta por cor exacta, só no que vai para dados/ (os PNG de origem não mudam).
RECOLOR_ACC = {
    (0xB7, 0x1C, 0x1C): (0xA2, 0x3B, 0x86),  # 0-3 m²/hab · a mais de 300 m  -> défice
    (0xE8, 0xA8, 0x38): (0xE6, 0xA6, 0xCC),  # 3-9 m²/hab                    -> insuficiente
    (0x2E, 0x7D, 0x32): (0x3E, 0x6A, 0xB3),  # > 9 m²/hab · a 300 m ou menos -> adequado
}


def _recolorir(p: Path, mapa: dict) -> str:
    """PNG com categorias de cor exacta -> data URI com as cores novas; falha se sobrar cor desconhecida."""
    import io

    import numpy as np
    from PIL import Image

    a = np.array(Image.open(p).convert("RGBA"))
    vis = a[..., 3] > 0
    feito = np.zeros(vis.shape, bool)
    for de, para in mapa.items():
        m = vis & (a[..., 0] == de[0]) & (a[..., 1] == de[1]) & (a[..., 2] == de[2])
        a[m, :3] = para
        feito |= m
    assert (feito == vis).all(), f"{p.name}: cores fora da paleta conhecida"
    buf = io.BytesIO()
    Image.fromarray(a, "RGBA").save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def dados_acessibilidade() -> dict:
    """Imagens das categorias (recoloridas), verde privado, candidatos e percentagens das Propostas.
    Os parques e o verde pago estão no contexto (comuns a vários temas)."""
    acc = RAIZ / "acessibilidade"
    cat = {
        "acc": ACC_LAYERS / "acessibilidade_2sfca.png",
        "acc_sim": ACC_LAYERS / "acessibilidade_2sfca_sim.png",
        "prox": ACC_LAYERS / "proximidade_300m.png",
        "prox_sim": ACC_LAYERS / "proximidade_simulada.png",
    }
    imgs = {k: _recolorir(p, RECOLOR_ACC) for k, p in cat.items()}
    imgs["baixa"] = _b64(ACC_LAYERS / "baixa_densidade.png")
    # todas as áreas (antes da correcção)
    imgs["privado"] = _b64(LAYERS / "interior_subsistente_colored.png")
    return {
        "imgs": imgs,
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
        k: round(float(v), 1) for k, v in c79.recortar_ao_porto(g).groupby("LC_1979_ab")["ha"].sum().items()
    }
    d["numeros"] = percentagens(RAIZ)
    d["incerteza"] = incerteza_epocas(hist / "incerteza.json")
    return d


def incerteza_epocas(caminho: Path) -> dict:
    """1σ (p.p.) da % de vegetação por época Landsat: erro-padrão dos anos da época; as épocas Landsat 8/9
    somam (em quadratura) o erro da ponte L8-L7. 1947 e 1979 (outra fonte) ficam sem valor."""
    import json
    import math

    if not caminho.exists():
        return {}
    j = json.loads(caminho.read_text(encoding="utf-8"))
    ponte = j["ponte_L8_L7"]["ep"] or 0.0
    out = {}
    for e in EPOCAS:
        if e in j and j[e]["ep"] is not None:
            ep = j[e]["ep"]
            out[e] = round(math.hypot(ep, ponte) if e in ("2016-17", "2023-24") else ep, 1)
    return out


def dados_regra() -> dict:
    """Regra 3-30-300: máscaras de edifícios por indicador (PNG de 1 bit, grelha de 3 m) e números.
    Gerados por regra_303030/mapa_png.py (ver regra_303030/CLAUDE.md); aqui só se embutem."""
    pasta = RAIZ / "regra_303030" / "layers"
    d = {k: "data:image/png;base64," + base64.b64encode((pasta / f"{k}.png").read_bytes()).decode()
         for k in ("todos", "nenhum", "c3", "c30", "c300")}
    d["numeros"] = json.loads((pasta / "numeros.json").read_text(encoding="utf-8"))
    return d


def _mascara_1bit(m) -> str:
    """Máscara booleana -> PNG de paleta a 1 bit (preto opaco onde True), em data URI."""
    import io

    import numpy as np
    from PIL import Image

    out = Image.fromarray(m.astype(np.uint8), mode="P")
    out.putpalette([0, 0, 0, 0, 0, 0])
    buf = io.BytesIO()
    out.save(buf, format="PNG", bits=1, optimize=True, transparency=bytes([0, 255]))
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def estatisticas() -> dict:
    """Hectares de cada camada dentro do concelho (contagem de píxeis da grelha da acessibilidade,
    2048 x 769, ~57 m² cada, máscara porto_mask.npy), população GHS-POP e m² de parque por habitante."""
    import numpy as np
    from PIL import Image

    mask = np.load(ACC_LAYERS / "porto_mask.npy")
    px = float(np.load(ACC_LAYERS / "calc_params.npz")["pixel_area_m2"])
    hist = RAIZ / "layers_historico"

    def ha(p: Path) -> float:
        a = np.array(Image.open(p).convert("RGBA"))[..., 3] > 0
        assert a.shape == mask.shape, f"{p.name}: grelha {a.shape} != {mask.shape}"
        return round(float((a & mask).sum()) * px / 1e4, 1)

    fontes = {
        "pago": ACC_LAYERS / "verde_pago_colored.png",
        "privado": LAYERS / "interior_subsistente_colored.png",
        "subsistente": LAYERS / "interior_subsistente_corrigido.png",
        "perdido": LAYERS / "interior_perdido.png",
        "centro_alargado": LAYERS / "centro_alargado.png",
        "perda": hist / "veg_perda.png",
        "ganho": hist / "veg_ganho.png",
    }
    fontes.update({k: LAYERS / f"{k}.png" for k in PNG_DADOS["hoje"]})
    s = {k: ha(p) for k, p in fontes.items()}
    parques = json.loads((RAIZ / "acessibilidade" / "parques_porto.geojson").read_text(encoding="utf-8"))
    s["parques_ha"] = round(sum(f["properties"].get("area_calc_ha") or 0 for f in parques["features"]), 1)
    s["pop"] = int(round(float(np.nansum(np.load(ACC_LAYERS / "pop_corrected.npy")[mask]))))
    s["m2hab"] = round(s["parques_ha"] * 1e4 / s["pop"], 1)
    s["concelho_ha"] = round(float(mask.sum()) * px / 1e4, 0)
    return s


def dados_contexto() -> dict:
    """Comum a todos os temas: limites, densidade, verde pago, parques (GeoJSON), água e área
    fora do concelho (fundo «Carta») e hectares por camada."""
    import numpy as np
    from PIL import Image

    d = {k: _b64(p) for k, p in PNG_DADOS["contexto"].items()}
    hist = RAIZ / "layers_historico"
    agua = np.array(Image.open(hist / "rio.png").convert("RGBA"))[..., 3] > 0
    # Douro e outras massas de água do OSM (mapa_unico/agua_osm.py); o oceano vem de rio.png
    agua |= np.array(Image.open(LAYERS / "agua_osm.png").convert("RGBA"))[..., 3] > 0
    porto = np.array(Image.open(hist / "porto_mask.png").convert("RGBA"))[..., 3] > 0
    d["agua"] = _mascara_1bit(agua)
    d["fora"] = _mascara_1bit(~porto & ~agua)  # o véu poupa a água, que fica azul como na V2b
    d["parques"] = json.loads((RAIZ / "acessibilidade" / "parques_porto.geojson").read_text(encoding="utf-8"))
    d["stats"] = estatisticas()
    return d


def dados_casos(raiz: Path = RAIZ, raiz_fontes: Path = None, raiz_media: Path = None) -> dict:
    """Tema Casos: lê `_casos/*.md` (só os revistos), valida (esquema, concelho, excertos, fotos) e
    devolve os casos prontos a embutir. Todo o texto sai escapado (a ficha usa innerHTML).
    Sem `raiz_fontes`/`raiz_media` usa os locais por omissão do validador."""
    import html
    import math
    from collections import defaultdict

    from casos_pipeline import validar
    from casos_pipeline.concelho import freguesia_de
    from casos_pipeline.modelo import GALERIAS, TIPOS, listar_casos

    raiz_fontes = validar.FONTES if raiz_fontes is None else raiz_fontes
    raiz_media = validar.MEDIA if raiz_media is None else raiz_media
    casos = listar_casos(raiz)
    for c in casos:
        erros = validar.validar_caso(c, raiz_fontes, raiz_media)
        if erros:
            raise ValueError(f"caso «{c['slug']}» inválido: " + "; ".join(erros))
    esc = lambda s: html.escape(str(s), quote=True)
    grupos = defaultdict(list)
    for c in casos:
        grupos[(c["lat"], c["lon"])].append(c)
    out = []
    for c in casos:
        lat, lon = c["lat"], c["lon"]
        g = grupos[(lat, lon)]
        if len(g) > 1 and g.index(c) > 0:  # coordenadas repetidas: círculo de 4 m, para os dois ficarem clicáveis
            ang = 2 * math.pi * g.index(c) / len(g)
            lat += 4 * math.sin(ang) / 111320
            lon += 4 * math.cos(ang) / (111320 * math.cos(math.radians(lat)))
        paragrafos = [p.strip() for p in c["corpo"].split(chr(10) * 2) if p.strip()]
        out.append({
            "slug": c["slug"], "titulo": esc(c["titulo"]), "galeria": c["galeria"], "tipo": c["tipo"],
            "lat": lat, "lon": lon, "aproximada": bool(c.get("aproximada")), "ano": esc(c["ano"]),
            "estado": c["estado"], "contestacao": esc(c["contestacao"]),
            "criterio": c["criterio"], "nota_editorial": esc(c.get("nota_editorial", "")),
            "freguesia": freguesia_de(c["lat"], c["lon"]),
            "corpo_html": "".join(f"<p>{esc(p)}</p>" for p in paragrafos),
            "fotos": [{"papel": f["papel"], "src": f"../Horrores/media/{c['slug']}/{f['ficheiro']}",
                       "ano": esc(f.get("ano", "")), "fonte": esc(f.get("fonte", "")), "url": esc(f["url"])}
                      for f in c.get("fotos") or []],
            "fotos_ligadas": [{"papel": f["papel"], "ano": esc(f.get("ano", "")), "fonte": esc(f.get("fonte", "")),
                               "url": esc(f["url"])} for f in c.get("fotos_ligadas") or []],
            "referencias": [{"titulo": esc(r["titulo"]), "url": esc(r["url"]), "data": esc(r.get("data", ""))}
                            for r in c["referencias"]],
            "url": f"../casos/{c['slug']}/",
        })
    return {"casos": out, "numeros": {
        "total": len(out),
        "por_tipo": {t: sum(x["tipo"] == t for x in out) for t in TIPOS},
        "por_galeria": {g: sum(x["galeria"] == g for x in out) for g in GALERIAS}}}


def escrever_dados() -> None:
    DADOS.mkdir(exist_ok=True)
    for nome, imgs in PNG_DADOS.items():
        if nome != "contexto":
            _escrever(nome, {k: _b64(p) for k, p in imgs.items()})
    _escrever("contexto", dados_contexto())
    _escrever("acessibilidade", dados_acessibilidade())
    _escrever("regra", dados_regra())
    _escrever("historico", dados_historico())
    _escrever("casos", dados_casos())


def _montar_html(temas, saida: Path, pagina: str, titulo: str, descricao: str, init: str = "", modelo: str = "template.html") -> None:
    js = (SRC / "core.js").read_text(encoding="utf-8")
    for t in temas:
        js += chr(10) + (SRC / f"tema_{t}.js").read_text(encoding="utf-8")
    html = (SRC / modelo).read_text(encoding="utf-8")
    html = (
        html.replace("/*CSS*/", (SRC / "estilo.css").read_text(encoding="utf-8"))
        .replace("<!--NAV-->", get_nav(pagina, depth=1, menu="barra", rodape="leitura") if modelo != "template.html" else get_nav(pagina, depth=1, menu="barra"))
        .replace("/*TITULO*/", titulo)
        .replace("/*DESC*/", descricao)
        .replace("/*INIT*/", init)
        .replace("/*JS*/", js)
    )
    saida.write_text(aplicar_chave(html), encoding="utf-8")
    print(f"{saida.relative_to(RAIZ)}  {saida.stat().st_size // 1024} KB")


def escrever_html() -> None:
    _montar_html(
        TEMAS, AQUI / "mapa_unico.html", PAGINA, "Mapa — Porto Verde",
        "Mapa interactivo do espaço verde do Porto: acessibilidade e propostas, mudanças 2016-2025, histórico desde 1947 e verde privado.")
    (RAIZ / "casos").mkdir(exist_ok=True)
    _montar_html(
        ["casos"], RAIZ / "casos" / "index.html", PAGINA_CASOS, "Horrores e sucessos — Porto Verde",
        "Mapa de horrores e sucessos: casos documentados no Porto, com fonte e fotos.",
        init="MU.URL_DADOS = '../mapa_unico/dados/'; "
             "MU.LIGACOES = [{rotulo: 'Mapa', href: './', on: true}, {rotulo: 'Lista', href: 'lista/'}];",
        modelo="template_casos.html")


if __name__ == "__main__":
    # --html: só o HTML (os dados do Histórico demoram ~2 min por causa das máscaras de 1947)
    # --casos: só os dados dos Casos (segundos) e o HTML
    if "--casos" in sys.argv:
        DADOS.mkdir(exist_ok=True)
        _escrever("casos", dados_casos())
    elif "--html" not in sys.argv:
        escrever_dados()
    escrever_html()
