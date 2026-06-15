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

# Páginas Jekyll-only (não têm nav Python — não entram em PAGES nem em TARGETS)
_JEKYLL_EXTRA = [
    ("sobre/", "Sobre"),
]
_GITHUB_URL = "https://github.com/coolio1/porto_areas_verdes_mudanca"


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
    lines.append(f'  <a href="{_GITHUB_URL}" target="_blank">GitHub</a>')
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

    return "<div id=\"nav\">\n" + "\n".join(lines) + "\n</div>"
