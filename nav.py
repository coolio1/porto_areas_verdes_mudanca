"""
nav.py — fonte única de verdade para a barra de navegação do site.

Quando adicionares uma nova página:
  1. Adiciona uma linha a PAGES
  2. Adiciona a entrada correspondente em patch_nav.py (TARGETS)
  3. Corre:  python patch_nav.py   (ou faz commit — o hook faz-o automaticamente)
"""

PAGES = [
    ("index.html",                                    "Início"),
    ("mapa.html",                                     "Mapa 2016-2025"),
    ("ndvi_historico.html",                           "Histórico 1947-2024"),
    ("interiores_quarteiroes.html",                   "Verde Privado"),
    ("acessibilidade/acessibilidade_verde.html",      "Acessibilidade"),
    ("acessibilidade/conversao_verde.html",           "Conversão"),
    ("atropelamentos/dashboard_atropelamentos.html",  "Atropelamentos"),
]


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
