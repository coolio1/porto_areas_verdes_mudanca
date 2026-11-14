"""
nav.py — fonte única de verdade para a barra de navegação do site.

Quando adicionares uma nova página:
  1. Adiciona uma linha a PAGES
  2. Adiciona a entrada correspondente em patch_nav.py (TARGETS)
  3. Corre:  python patch_nav.py   (ou faz commit — o hook faz-o automaticamente)

Para páginas Jekyll (_layouts/default.html):
  A nav é gerada em _includes/nav.html por get_jekyll_nav().
  patch_nav.py regenera-a automaticamente — não editar _includes/nav.html à mão.
"""

PAGES = [
    ("index.html", "Início"),
    ("mapa_unico/mapa_unico.html", "Mapas e uso do solo"),
    ("50espacos/", "50 Espaços Verdes"),
    ("Mobilidade/autocarros.html", "Mobilidade"),
]

# «Mobilidade» é um só item de menu com dois separadores (barra por baixo do menu, só nestas páginas).
# A página dos atropelamentos acende «Mobilidade» no menu (alias) e não tem item próprio.
ABAS_MOBILIDADE = [
    ("Mobilidade/autocarros.html", "Autocarros: mapa"),
    ("Mobilidade/analise.html", "Autocarros: análise"),
    ("atropelamentos/dashboard_atropelamentos.html", "Atropelamentos"),
]
_ALIAS_ACTIVO = {"atropelamentos/dashboard_atropelamentos.html": "Mobilidade/autocarros.html",
                 "Mobilidade/analise.html": "Mobilidade/autocarros.html"}

# Páginas Jekyll-only (não entram em PAGES nem em TARGETS mas aparecem em AMBOS os navs)
_JEKYLL_EXTRA = [
    ("artigos/", "Artigos"),
    ("sobre/", "Sobre"),
]


# Condição Liquid que acende cada item no menu Jekyll (o mapa único e a Mobilidade não são páginas Jekyll)
_ACTIVO_JEKYLL = {
    "index.html": 'page.url == "/"',
    "50espacos/": 'page.url contains "/50espacos"',
    "artigos/": 'page.url contains "/artigos" or page.layout == "post"',
    "sobre/": 'page.url contains "/sobre"',
}


def get_jekyll_nav():
    """
    Devolve o bloco <nav>...</nav> para Jekyll (_includes/nav.html).
    Usa {{ site.baseurl }} — processado pelo Liquid em build time.
    O item da página actual leva class="active" (condições em _ACTIVO_JEKYLL).
    """
    base = "{{ site.baseurl }}"
    lines = []
    for canonical, label in PAGES + _JEKYLL_EXTRA:
        href = base + "/" if canonical == "index.html" else base + "/" + canonical
        cond = _ACTIVO_JEKYLL.get(canonical)
        activo = f'{{% if {cond} %}} class="active"{{% endif %}}' if cond else ""
        lines.append(f'  <a href="{href}"{activo}>{label}</a>')
    return "<nav>\n" + "\n".join(lines) + "\n</nav>"


# ---------- Moldura comum: CSS e rodapé (porto-verde.css) ----------
CSS_COMUM = "assets/css/porto-verde.css"
FONTES_PADRAO = "Sentinel-2, Landsat, OSM, PDM Porto"
# Fontes de dados por página (canonical -> texto). Sem entrada: FONTES_PADRAO.
FONTES = {
    "Mobilidade/autocarros.html": "Associação Porto Digital (posições dos autocarros), OSM",
    "atropelamentos/dashboard_atropelamentos.html": "ANSR, INE",
    "Mobilidade/analise.html": (
        "Associação Porto Digital (posições dos autocarros), STCP (horários), "
        "Câmara Municipal do Porto (corredores BUS e semáforos), OSM"
    ),
}


def get_css_link(depth=0):
    """<link> para o CSS comum; vai no início do bloco do menu (válido no <body>)."""
    return f'<link rel="stylesheet" href="{"../" * depth}{CSS_COMUM}">\n'


def _rodape(modo, href_indice, href_logo, fontes, sem_logo_na_inicial=False):
    logo = f'<a class="pv-rodape__logo" href="{href_indice}"><img src="{href_logo}" alt="Porto Verde"></a>'
    if sem_logo_na_inicial:  # a página inicial já tem o logótipo grande no cabeçalho
        logo = '{% unless page.url == "/" %}' + logo + "{% endunless %}"
    return (
        f'<footer class="pv-rodape pv-rodape--{modo}">\n'
        f"  {logo}\n"
        f'  <p><a href="https://coolio1.github.io/" target="_blank" rel="noopener">Nuno Quental</a><br>\n'
        f"  Dados abertos: {fontes}</p>\n"
        "</footer>"
    )


def get_rodape(active_canonical, depth=0, modo="leitura"):
    """Rodapé para páginas geradas. modo: 'leitura' (fim da página) ou 'mapa' (etiqueta fixa em baixo)."""
    prefix = "../" * depth
    fontes = FONTES.get(active_canonical, FONTES_PADRAO)
    return _rodape(modo, prefix + "index.html", prefix + "favicon.png", fontes)


def get_rodape_jekyll():
    """Rodapé para Jekyll (_includes/rodape.html); fontes por página via front matter `fontes:`."""
    return _rodape(
        "leitura", "{{ site.baseurl }}/", "{{ site.baseurl }}/favicon.png",
        '{{ page.fontes | default: "' + FONTES_PADRAO + '" }}',
        sem_logo_na_inicial=True,
    )


def get_nav(active_canonical, depth=0):
    """
    Devolve o bloco <div id="nav">...</div> com os links correctos.

    active_canonical: caminho da página actual relativo à raiz do projecto
                      (ex: "mapa.html" ou "acessibilidade/acessibilidade_verde.html")
    depth: profundidade do directório (0 = raiz, 1 = uma subpasta)
    """
    prefix = "../" * depth
    current_dir = "/".join(active_canonical.split("/")[:-1])

    lines = []
    for canonical, label in PAGES:
        if depth > 0:
            target_dir = "/".join(canonical.split("/")[:-1])
            href = (
                canonical.split("/")[-1]
                if current_dir == target_dir
                else prefix + canonical
            )
        else:
            href = canonical

        cls = ' class="active"' if canonical == _ALIAS_ACTIVO.get(active_canonical, active_canonical) else ""
        lines.append(f'  <a href="{href}"{cls}>{label}</a>')

    for path, label in _JEKYLL_EXTRA:
        href = prefix + path if depth > 0 else path
        lines.append(f'  <a href="{href}">{label}</a>')

    return '<div id="nav">\n' + "\n".join(lines) + "\n</div>"


def get_abas_mobilidade(active_canonical, depth=1, fundo_no_telemovel=False):
    """Barra de separadores Autocarros | Atropelamentos, fixa por baixo do menu (páginas em subpasta).

    `fundo_no_telemovel`: em ecrãs estreitos fica junto ao fundo (páginas com título por baixo do menu).
    """
    movel = ("bottom:10px;left:8px;right:8px;top:auto;justify-content:center" if fundo_no_telemovel
             else "top:70px;right:8px")
    prefix = "../" * depth
    current_dir = "/".join(active_canonical.split("/")[:-1])
    links = []
    for canonical, label in ABAS_MOBILIDADE:
        mesma_pasta = "/".join(canonical.split("/")[:-1]) == current_dir
        href = canonical.split("/")[-1] if mesma_pasta else prefix + canonical
        cls = ' class="on"' if canonical == active_canonical else ""
        links.append(f'<a href="{href}"{cls}>{label}</a>')
    return (
        '<div id="abas-mobilidade">\n'
        "<style>#abas-mobilidade{position:fixed;top:40px;right:10px;z-index:1000;display:flex;gap:2px;"
        "font:12px 'Segoe UI',Arial,sans-serif;background:rgba(255,255,255,.92);border-radius:6px;padding:2px;"
        "box-shadow:0 1px 4px rgba(0,0,0,.15)}"
        "#abas-mobilidade a{color:#444;text-decoration:none;padding:4px 12px;border-radius:5px}"
        "#abas-mobilidade a.on{background:var(--pv-verde,#0B5232);color:#fff}"
        f"@media(max-width:700px){{#abas-mobilidade{{{movel}}}}}</style>\n  "
        + "\n  ".join(links)
        + "\n</div>"
    )


def get_footer_logo(depth=0):
    """
    Devolve o bloco <div id="footer-logo">...</div> para mapas standalone.
    Logo centrado no fundo com o link para o index e crédito "Nuno Quental".
    Esconde o #credit original via <style> inline.
    """
    prefix = "../" * depth
    return (
        '<div id="footer-logo" style="position:fixed;bottom:28px;right:10px;'
        'z-index:1000;text-align:center;pointer-events:none;">\n'
        "  <style>#credit{display:none!important}"
        "@media(max-width:768px){#footer-logo{display:none!important}}</style>\n"
        f'  <a href="{prefix}index.html" style="display:inline-block;pointer-events:auto;">'
        f'<img src="{prefix}assets/images/logo-porto-verde.png" alt="Porto Verde"'
        ' style="height:52px;width:auto;border-radius:0;display:block;margin:0 auto;'
        'filter:drop-shadow(0 1px 3px rgba(0,0,0,0.2));"></a>\n'
        '  <a href="https://coolio1.github.io/" target="_blank"'
        " style=\"display:block;margin-top:3px;font:10px 'Segoe UI',Arial,sans-serif;"
        'color:#888;text-decoration:none;pointer-events:auto;">Nuno Quental</a>\n'
        "</div>"
    )
