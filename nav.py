"""nav.py — atalho de compatibilidade para os geradores de páginas.

O menu, as abas da Mobilidade e o rodapé vivem num só sítio: assets/js/moldura.js
(desenha-os no browser; mudar lá = todas as páginas mudam, sem regenerar nada).
Os geradores que chamam get_nav() recebem apenas a etiqueta <script> que a carrega.
"""


def get_nav(active_canonical, depth=0, **dados):
    """<script> da moldura. `dados`: atributos data-* extra (menu, rodape, fontes)."""
    extra = "".join(f' data-{k}="{v}"' for k, v in dados.items())
    return (f'<script src="{"../" * depth}assets/js/moldura.js" '
            f'data-pagina="{active_canonical}"{extra}></script>')


def get_abas_mobilidade(*_args, **_kw):
    return ""  # as abas saem de moldura.js (ABAS)


def get_footer_logo(*_args, **_kw):
    return ""  # o rodapé sai de moldura.js
