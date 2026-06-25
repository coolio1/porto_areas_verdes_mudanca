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
    ("index.html",                                    "Início"),
    ("mapa.html",                                     "Mapa 2016-2025"),
    ("ndvi_historico.html",                           "Histórico 1947-2024"),
    ("interiores_quarteiroes.html",                   "Verde Privado"),
    ("acessibilidade/acessibilidade_verde.html",      "Acessibilidade"),
    ("acessibilidade/conversao_verde.html",           "Propostas"),
    ("atropelamentos/dashboard_atropelamentos.html",  "Atropelamentos"),
]

# Páginas Jekyll-only (não entram em PAGES nem em TARGETS mas aparecem em AMBOS os navs)
_JEKYLL_EXTRA = [
    ("artigos/", "Artigos"),
    ("sobre/", "Sobre"),
]


def get_jekyll_nav():
    """
    Devolve o bloco <nav>...</nav> para Jekyll (_includes/nav.html).
    Usa {{ site.baseurl }} — processado pelo Liquid em build time.
    """
    base = "{{ site.baseurl }}"
    lines = []
    for canonical, label in PAGES:
        href = base + "/" if canonical == "index.html" else base + "/" + canonical
        lines.append(f'  <a href="{href}">{label}</a>')
    for path, label in _JEKYLL_EXTRA:
        lines.append(f'  <a href="{base}/{path}">{label}</a>')
    return "<nav>\n" + "\n".join(lines) + "\n</nav>"


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
            href = canonical.split("/")[-1] if current_dir == target_dir else prefix + canonical
        else:
            href = canonical

        cls = ' class="active"' if canonical == active_canonical else ""
        lines.append(f'  <a href="{href}"{cls}>{label}</a>')

    for path, label in _JEKYLL_EXTRA:
        href = prefix + path if depth > 0 else path
        lines.append(f'  <a href="{href}">{label}</a>')

    return "<div id=\"nav\">\n" + "\n".join(lines) + "\n</div>"


def get_footer_logo(depth=0):
    """
    Devolve o bloco <div id="footer-logo">...</div> para mapas standalone.
    Logo centrado no fundo com o link para o index e crédito "Nuno Quental".
    Esconde o #credit original via <style> inline.
    """
    prefix = "../" * depth
    return (
        '<div id="footer-logo" style="position:fixed;bottom:10px;right:10px;'
        'z-index:1000;text-align:center;pointer-events:none;">\n'
        '  <style>#credit{display:none!important}'
        '@media(max-width:768px){#footer-logo{display:none!important}}</style>\n'
        f'  <a href="{prefix}index.html" style="display:inline-block;pointer-events:auto;">'
        f'<img src="{prefix}assets/images/logo-porto-verde.png" alt="Porto Verde"'
        ' style="height:52px;width:auto;border-radius:0;display:block;margin:0 auto;'
        'filter:drop-shadow(0 1px 3px rgba(0,0,0,0.2));"></a>\n'
        '  <a href="https://coolio1.github.io/" target="_blank"'
        ' style="display:block;margin-top:3px;font:10px \'Segoe UI\',Arial,sans-serif;'
        'color:#888;text-decoration:none;pointer-events:auto;">Nuno Quental</a>\n'
        '</div>'
    )
