import re
import subprocess
import sys
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

SP = Path(__file__).parent
A = "C:/Users/quent/OneDrive/Claude/Porto Verde/assets/images/"
s = (SP / "nota.md").read_text(encoding="utf-8")

# G19 (2026-11-08): números, graus de certeza e referências da nota provados por nota.factos.md
# (excerto lido ou conta recalculada). Falhas impedem o PDF; sem ficheiro, aviso bem visível.
_FACTOS = SP / "nota.factos.md"
if _FACTOS.exists():
    _r = subprocess.run(
        [
            sys.executable, '-I', '-X', 'utf8',
            str(Path.home() / '.claude/scripts/research_fetch.py'),
            'factos', str(SP), '--texto', str(SP / 'nota.md'),
            '--factos', str(_FACTOS),
        ],
        capture_output=True, text=True, encoding='utf-8', check=False,
    )
    print(_r.stdout)
    if _r.returncode:
        sys.exit('G19: a nota tem números, graus ou referências sem prova em nota.factos.md; PDF não gerado')
else:
    print('AVISO G19: sem nota.factos.md; números, graus e referências NÃO verificados')
l = s.split("\n", 2)
meta = l[0] + "\n" + l[1] + "\n"
rest = l[2]
# o Resumo sai do PDF (pedido do utilizador, 2026-11-07): a página Conclusões faz esse papel
_i, _j = rest.index("## Resumo"), rest.index("## 1 Introdução")
rest = rest[:_i] + rest[_j:]

titulo_full = l[0].lstrip("% ").strip()
titulo, _, sub = titulo_full.partition(": ")
sub = sub[:1].upper() + sub[1:]


# ---------- figuras ----------
def fig(n, cap):
    return f'\n<div class="graf"><img src="{A}habitacao-{n}.png"><p class="leg">{cap}</p></div>\n\n'


FIGS = [
    (
        "O debate público atribui esta subida",
        "fig1-serie-2008-2025",
        "Figura 1. Preços das casas e rendimento disponível bruto das famílias em Portugal, 2008–2025 (índice, 2008 = 100, valores correntes). Fonte: Eurostat.",
    ),
    (
        "### 3.2 Imigração",
        "fig3-choques-v2",
        "Figura 2. Os cinco choques na procura, com números-chave de cada um.",
    ),
    (
        "### 3.6 ",
        "fig2-oferta",
        "Figura 3. Três sinais do lado da oferta em Portugal: licenciamentos, municípios em que as famílias cresceram mais do que os alojamentos (2011–2021 e 2021–2024) e prazos de licenciamento.",
    ),
    (
        "### 3.9 ",
        "fig5-habitacao-publica",
        "Figura 4. Peso do parque social ou a custo controlado no total de habitações.",
    ),
    (
        "### 3.12 ",
        "fig6-vazios",
        "Figura 5. Fogos vagos, fora do mercado e em bom estado, e devolutos com IMI agravado, em Lisboa e no Porto.",
    ),
    (
        "### 4.2 ",
        "fig4-efeitos-precos",
        "Figura 6. Efeito estimado de várias medidas nos preços, em estudos de contextos diferentes (ordens de grandeza, não comparáveis ao ponto).",
    ),
    (
        "## 6 Limitações",
        "fig7-roteiro",
        "Figura 7. Roteiro das recomendações por horizonte temporal.",
    ),
]
for anchor, n, cap in FIGS:
    assert rest.count(anchor) == 1, anchor
    rest = rest.replace(anchor, fig(n, cap) + anchor, 1)

# ---------- frases em destaque (verbatim do texto) ----------
PULLS = [
    (
        "## 1 Introdução",
        "Não existe, para Portugal, uma decomposição publicada que atribua a cada factor uma parte da subida dos preços.",
        2,
    ),
    (
        "### 3.3 ",
        "O crescimento do AL foi muito rápido e concentrado em poucos anos.",
        1,
    ),
    (
        "#### 3.11.5 ",
        "As fontes oficiais estimam que a fracção mobilizável a curto prazo é uma pequena parte do total de vagos.",
        1,
    ),
    (
        "### 3.17 ",
        "A protecção da estrutura ecológica, das linhas de água e das áreas inundáveis, a área verde protegida e o acesso a espaço verde a menos de 800 m são compatíveis com as recomendações e este artigo adopta-os.",
        2,
    ),
]


def pull_after_para(text, anchor, quote, idx):
    assert text.count(anchor) == 1, anchor
    i = text.index(anchor)
    nxt = re.search(r"\n#{2,4} ", text[i + 3 :])
    end = i + 3 + nxt.start() if nxt else len(text)
    assert quote in text[i:end], (anchor, "citação fora da secção")
    pos = text.index("\n\n", i)  # fim da linha do título
    n = -1
    while True:
        k = text.find("\n\n", pos + 2)
        blk = text[pos + 2 : k]
        pos_next = k
        if blk.strip() and not blk.startswith(("<div", ":::", "|", "- ", "1. ")):
            n += 1
            if n == idx:
                break
        pos = pos_next
        assert pos < end, (anchor, "sem parágrafo")
    q = quote[:1].upper() + quote[1:]
    q = q if q.endswith((".", "?", "!")) else q + "."
    box = "\n\n::: destaque\n" + q + "\n:::\n"
    return text[:k] + box + text[k:]


for anchor, quote, idx in PULLS:
    rest = pull_after_para(rest, anchor, quote, idx)

# ---------- capa, síntese e índice ----------
cover = f"""
<div class="capa">
<img class="hero" src="{A}habitacao-ilustracao-casas.jpg"><div class="veu"></div>
<div class="topo"><span>Nota de investigação · Novembro de 2026</span><img class="logo" src="{A}logo-porto-verde.png"></div>
<h1>{titulo.replace(" da habitação", "<br>da habitação").replace(" em Lisboa", "<br>em Lisboa")}</h1>
<div class="base"><p class="sub">{sub}</p>
<div class="meta"><div><b>Porto Verde</b><br>Estudo de síntese · __NPAG__ páginas</div><div style="text-align:right">Ilustração gerada por<br>inteligência artificial</div></div>
<p class="aviso"><b>Aviso:</b> Este artigo foi gerado com recurso a inteligência artificial e não reflecte necessariamente a opinião do autor.</p></div>
</div>

"""

import sys

sys.path.insert(0, str(SP / "modelo"))
import conclusoes

sintese = conclusoes.html(img=f"{A}habitacao-ilustracao-casas.jpg") + "\n\n"

heads = [
    (len(m.group(1)), m.group(2).strip())
    for m in re.finditer(r"^(##|###) (.+)$", rest, re.MULTILINE)
]
heads = [(lv, t) for lv, t in heads]


def toc_html(pages):
    out = ['<div class="toc"><h2>Índice</h2><ul>']
    for i, (lv, t) in enumerate(heads):
        p = pages.get(i, "") if pages else ""
        mm = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", t)
        num, txt = (mm.group(1), mm.group(2)) if mm else ("", t)
        if lv == 2 and num:
            num += "."
        out.append(
            f'<li class="n{lv}"><a href="#sec{i}"><span class="tn">{num}</span>'
            f'<span class="t">{txt}</span><span class="d"></span><span class="p">{p}</span></a></li>'
        )
    out.append("</ul></div>\n\n")
    return "\n".join(out)


def nohyphen(path):
    """Palavras com hífen não se partem ao fim da linha (excepto URLs e referências)."""
    from bs4 import BeautifulSoup, NavigableString

    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    nb = chr(160)
    for node in list(soup.find_all(string=True)):
        if node.parent.name in ("script", "style"):
            continue
        t0 = str(node)
        t1 = re.sub(r"(\d)\s(%|€|mil\b|milhões\b)", r"\1" + nb + r"\2", t0)
        t1 = re.sub(r"(?<=\d)\s(?=\d{3}\b)", nb, t1)
        t1 = re.sub(r"(?<=\d)\s(?=(?:p\.p\.|km|m²|kg|dias|anos|meses)\b)", nb, t1)
        if t1 != t0:
            node.replace_with(NavigableString(t1))
    pat0 = re.compile(r"(?<![\w/.:@])[^\W_]+(?:-[^\W_]+)+(?![\w/@])")
    # referências: só palavras soltas (nomes, termos); nunca pedaços de URL
    pat1 = re.compile(r"(?<!\S)[^\W_]+(?:-[^\W_]+)+(?=[\s,;:)]|$)")
    for node in list(soup.find_all(string=True)):
        if node.parent.name in ("script", "style", "a", "code"):
            continue
        pat = pat1 if node.find_parent(id="referências") else pat0
        txt = str(node)
        if "-" not in txt or not pat.search(txt):
            continue
        frag = BeautifulSoup("", "html.parser")
        pos = 0
        out = []
        for m in pat.finditer(txt):
            out.append(NavigableString(txt[pos : m.start()]))
            sp = frag.new_tag("span", attrs={"class": "nq"})
            sp.string = m.group(0)
            out.append(sp)
            pos = m.end()
        out.append(NavigableString(txt[pos:]))
        node.replace_with(*out)
    path.write_text(str(soup), encoding="utf-8")


def ids_titulos(texto):
    cont = [-1]

    def f(mo):
        cont[0] += 1
        h, t = mo.group(1), mo.group(2)
        if h == "##":
            t = re.sub(r"^(\d+) ", r'<span class="num">\1</span> ', t)
        return f'{h} <span id="sec{cont[0]}"></span>{t}'

    return re.sub(r"^(##|###) (.+)$", f, texto, flags=re.MULTILINE)


def render(pages):
    (SP / "nota2.md").write_text(
        meta
        + cover.replace("__NPAG__", NPAG)
        + sintese
        + toc_html(pages)
        + ids_titulos(rest),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "pandoc",
            str(SP / "nota2.md"),
            "-s",
            "--section-divs",
            "--css",
            str(SP / "nota.css"),
            "--embed-resources",
            "-f",
            "markdown+pipe_tables+fenced_divs",
            "-V",
            "lang=pt-PT",
            "-o",
            str(SP / "nota.html"),
        ],
        check=True,
    )
    nohyphen(SP / "nota.html")
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto((SP / "nota.html").as_uri())
        pg.pdf(
            path=str(SP / "nota_raw.pdf"),
            prefer_css_page_size=True,
            print_background=True,
        )
        b.close()


def norm(x):
    return re.sub(r"\s+", " ", x)


def find_pages():
    d = pymupdf.open(str(SP / "nota_raw.pdf"))
    texts = [norm(pg.get_text()) for pg in d]
    start = next(i for i in range(3, len(d)) if "Introdução" in texts[i][:30])
    res = {}
    cur = start
    for i, (lv, t) in enumerate(heads):
        key = norm(t)[:20]
        key2 = norm(re.sub(r"^\d+ ", "", t))[:32]
        for pgi in range(cur, len(d)):
            if (
                key2 in re.sub(r"[\d\x00]", "", texts[pgi])
                if lv == 2
                else key in texts[pgi]
            ):
                res[i] = pgi + 1
                cur = pgi
                break
        else:
            raise SystemExit(f"título não encontrado: {t}")
    return res, d


NPAG = "80"
render(None)
pages, d = find_pages()
d.close()
render(pages)
pages2, d = find_pages()
assert pages2 == pages, "índice mudou entre passagens"

# ---------- marcadores e rodapé ----------
toc = [[lv - 1, re.sub(r"^(\d+) ", r"\1. ", t) if lv == 2 else t, pages[i]] for i, (lv, t) in enumerate(heads)]
d.set_toc(toc)
n = len(d)
for i in range(2, n):
    pg = d[i]
    w, h = pg.rect.width, pg.rect.height
    pg.draw_line((60, h - 40), (w - 60, h - 40), color=(0.65, 0.78, 0.6), width=0.6)
    pg.insert_text(
        (60, h - 27),
        "Porto Verde  ·  Subida do preço da habitação em Lisboa e Porto",
        fontname="helv",
        fontsize=8,
        color=(0.4, 0.4, 0.4),
    )
    num = f"{i + 1}"
    pg.insert_text(
        (w - 60 - 5 * len(num), h - 27),
        num,
        fontname="helv",
        fontsize=9,
        color=(0.18, 0.49, 0.2),
    )
d.save(str(SP / "nota_v26.pdf"), garbage=3, deflate=True)
print(n, "páginas")
(SP / "pv").mkdir(exist_ok=True)
for k in (0, 1, 2, 3, 4):
    d[k].get_pixmap(dpi=55).save(str(SP / "pv" / f"n{k + 1}.png"))
