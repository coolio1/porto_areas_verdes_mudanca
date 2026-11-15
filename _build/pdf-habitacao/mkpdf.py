import os
import re
import subprocess
import sys
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

SP = Path(__file__).parent
# saídas (nota2.md, HTML, PDF): PDF_OUT, p. ex. a scratchpad (escrever na pasta do OneDrive falha com «Bad file descriptor»)
OUT = Path(os.environ.get("PDF_OUT") or SP)
OUT.mkdir(parents=True, exist_ok=True)
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
# a Introdução e as Recomendações saem (pedido do utilizador, 2026-11-14): a Síntese científica
# (secção 1, escrita no artigo) absorve-as; as Limitações passam a 5 e a nota não remete para 1, 5 ou 6
_i, _j = rest.index("## 1 Introdução"), rest.index("## 2 Métodos")
rest = rest[:_i] + rest[_j:]
_i, _j = rest.index("## 5 Recomendações"), rest.index("## 6 Limitações")
rest = rest[:_i] + rest[_j:]
rest = rest.replace("## 6 Limitações", "## 5 Limitações", 1)

titulo_full = l[0].lstrip("% ").strip()
titulo, _, sub = titulo_full.partition(": ")
sub = sub[:1].upper() + sub[1:]


# ---------- figuras ----------
def fig(n, cap):
    cap = re.sub(r"^(Figura \d+)\.", r'<span class="fl">\1</span>', cap)
    return f'\n<div class="graf"><img src="{A}habitacao-{n}.png"><p class="leg">{cap}</p></div>\n\n'


FIGS = [
    (
        "### 3.2 Imigração",
        "fig3-choques-v2",
        "Figura 4. Os cinco choques na procura, com números-chave de cada um.",
    ),
    (
        "### 3.6 ",
        "fig2-oferta",
        "Figura 5. Três sinais do lado da oferta em Portugal: licenciamentos, municípios em que as famílias cresceram mais do que os alojamentos (2011–2021 e 2021–2024) e prazos de licenciamento.",
    ),
    (
        "### 3.9 ",
        "fig5-habitacao-publica",
        "Figura 6. Peso do parque social ou a custo controlado no total de habitações.",
    ),
    (
        "### 3.12 ",
        "fig6-vazios",
        "Figura 7. Fogos vagos, fora do mercado e em bom estado, e devolutos com IMI agravado, em Lisboa e no Porto.",
    ),
]
# figuras da Síntese científica (secção 1): mesma imagem do artigo, legenda do PDF
FIGS_SINTESE = {
    "habitacao-fig1-serie-2008-2025": (
        "fig1-serie-2008-2025",
        "Figura 1. Preços das casas e rendimento disponível bruto das famílias em Portugal, 2008–2025 (índice, 2008 = 100, valores correntes). Fonte: Eurostat.",
    ),
    "habitacao-fig4-efeitos-precos": (
        "fig4-efeitos-precos",
        "Figura 2. Efeito estimado de várias medidas nos preços, em estudos de contextos diferentes (ordens de grandeza, não comparáveis ao ponto).",
    ),
}
FIG_ROTEIRO = (
    "fig7-roteiro",
    "Figura 3. Roteiro das recomendações por horizonte temporal.",
)
for anchor, n, cap in FIGS:
    assert rest.count(anchor) == 1, anchor
    rest = rest.replace(anchor, fig(n, cap) + anchor, 1)

# ---------- frases em destaque (verbatim do texto) ----------
PULLS = [
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


# ---------- Síntese científica (secção 1): vem do artigo, única fonte ----------
def sintese_cientifica():
    post = (SP.parent.parent / "_posts" / "2026-11-05-habitacao-lisboa-porto.md").read_text(encoding="utf-8")
    a, b = post.index("## Síntese científica\n"), post.index("## A nota completa (PDF)")
    t = post[a:b].rstrip() + "\n"
    t = t.replace("## Síntese científica", "## 1 Síntese científica", 1)
    k = [0]

    def h3(m):
        k[0] += 1
        return f"### 1.{k[0]} " + re.sub(r"^\d+\.\s+", "", m.group(1))

    t = re.sub(r"^### (.+)$", h3, t, flags=re.MULTILINE)

    def img(m):
        n, cap = FIGS_SINTESE[m.group(1)]
        return fig(n, cap).strip("\n") + "\n"

    t = re.sub(
        r"!\[[^\]]*\]\(\{\{ site\.baseurl \}\}/assets/images/([^)]+)\.png\)\n\*[^\n]*\*\n", img, t
    )
    t = t.replace("{: .tabela-texto}\n", "")
    t = t.replace(" da nota completa)", ")")
    t = t.replace(
        "remetem para a lista de referências da nota completa (PDF)",
        "remetem para as Referências, no fim do documento",
    )
    marca = "Grau de certeza: **"
    assert t.count(marca) == 1
    t = t.replace(marca, fig(*FIG_ROTEIRO).strip("\n") + "\n\n" + marca)
    assert "{{" not in t and "{%" not in t and "site.baseurl" not in t, "restos de Liquid na síntese"
    return t


rest = sintese_cientifica() + "\n" + rest

# ---------- capa, síntese e índice ----------
cover = f"""
<div class="capa"><div class="gr"></div><div class="in">
<div class="cab"><span class="marca"><i></i>Porto Verde</span><span class="lab">Nota 02 · Dossier de síntese · Novembro 2026</span></div>
<div style="display:flex;flex-direction:column;gap:3mm;margin-top:2mm"><span class="lab" style="color:#E0A033">Investigação · Habitação · Lisboa e Porto</span>
<h1>{titulo}</h1><p class="sub">{sub}</p></div>
<div class="fig"><img src="{A}habitacao-ilustracao-casas.jpg"><span class="lab">Fig. 0 · Ilustração gerada por inteligência artificial</span></div>
<div class="nums"><div><b class="a">+145&nbsp;%</b><span class="lab">Preços das casas · 2008–2025</span></div><div><b>+69&nbsp;%</b><span class="lab">Rendimento das famílias · 2008–2025</span></div></div>
<div class="dossier"><span class="lab" style="opacity:.8">Neste dossier</span><div class="tiles">
<div class="tile" style="--c:#E0A033"><span class="lab">01</span><b>Síntese científica</b></div>
<div class="tile" style="--c:#3F9C80"><span class="lab">02</span><b>Métodos</b></div>
<div class="tile" style="--c:#19A06B"><span class="lab">03</span><b>Resultados</b></div>
<div class="tile" style="--c:#D9642B"><span class="lab">04</span><b>Discussão</b></div>
<div class="tile" style="--c:#6F9BE0"><span class="lab">05</span><b>Limitações</b></div>
<div class="tile" style="--c:#9AA8A2"><span class="lab">06</span><b>Referências</b></div></div></div>
<p class="aviso">Valores nominais. Este artigo foi gerado com recurso a inteligência artificial e não reflecte necessariamente a opinião do autor. As recomendações das subsecções 1.6 e 1.7 são inferências da síntese a partir dos estudos, não resultados deles. __NPAG__ páginas. portoverde.pt</p>
</div></div>

"""

import sys

sys.path.insert(0, str(SP / "modelo"))
import conclusoes

sintese = conclusoes.html_e() + "\n\n"

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
    # a abertura nasce no fim da secção anterior (o pandoc só envolve o título): passa a irmã da sua secção
    for ab in soup.select("div.abertura"):
        prev = ab.find_parent("section", class_="level2")
        if prev is not None:
            ab.extract()
            prev.insert_after(ab)
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
    pat0 = re.compile(r"(?<![\w/.:@])[^\W_]+(?:-[^\W_]+)+(?:/\d+)?(?![\w/@])")
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
    # o html.parser passa os atributos a minúsculas; o viewBox do SVG tem de manter a caixa
    path.write_text(str(soup).replace(" viewbox=", " viewBox="), encoding="utf-8")


SECCOES = {"1": "#E0A033", "2": "#3F9C80", "3": "#19A06B", "4": "#D9642B", "5": "#6F9BE0", "": "#9AA8A2"}


def abertura(i, pages):
    """Página escura de abertura da secção, com a lista das subsecções e as suas páginas."""
    t = heads[i][1]
    mm = re.match(r"^(\d+)\s+(.*)$", t)
    num, txt = (mm.group(1), mm.group(2)) if mm else ("", t)
    cor = SECCOES.get(num, SECCOES[""])
    subs = []
    for k in range(i + 1, len(heads)):
        if heads[k][0] == 2:
            break
        m3 = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", heads[k][1])
        if m3:
            subs.append((m3.group(1), m3.group(2), pages.get(k, "") if pages else ""))
    lis = "".join(
        f'<li><span class="tn">{a}</span><span class="tt">{b}</span><span class="pp">{c}</span></li>'
        for a, b, c in subs
    )
    cls = "sub dois" if len(subs) > 9 else "sub"
    bloco = f'<div class="{cls}"><span class="lab">Nesta secção</span><ul>{lis}</ul></div>' if subs else ""
    return (
        f'::: {{.abertura style="--c:{cor}"}}\n'
        f'<div class="gr"></div><div class="in"><div class="cab"><span class="lab">Porto Verde · Nota 02</span>'
        f'<span class="lab">Secção {num or "—"}</span></div>'
        f'<div class="n">{num or "·"}</div><div class="t">{txt}</div>{bloco}</div>\n:::\n\n'
    )


def ids_titulos(texto, pages=None):
    cont = [-1]

    def f(mo):
        cont[0] += 1
        h, t = mo.group(1), mo.group(2)
        pre = ""
        if h == "##":
            pre = abertura(cont[0], pages)
            t = re.sub(r"^(\d+) ", r'<span class="num">\1</span> ', t)
        else:
            t = re.sub(r"^(\d+(?:\.\d+)+) ", r'<span class="tn">\1</span> ', t)
        return f'{pre}{h} <span id="sec{cont[0]}"></span>{t}'

    return re.sub(r"^(##|###) (.+)$", f, texto, flags=re.MULTILINE)


def render(pages):
    (OUT / "nota2.md").write_text(
        meta
        + cover.replace("__NPAG__", NPAG)
        + sintese
        + toc_html(pages)
        + ids_titulos(rest, pages),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "pandoc",
            str(OUT / "nota2.md"),
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
            str(OUT / "nota.html"),
        ],
        check=True,
    )
    nohyphen(OUT / "nota.html")
    with sync_playwright() as p:
        # PW_CHROME: caminho do Chromium instalado, se a versão do playwright não casar com a cache
        b = p.chromium.launch(executable_path=os.environ.get("PW_CHROME") or None)
        pg = b.new_page()
        pg.goto((OUT / "nota.html").as_uri())
        pg.pdf(
            path=str(OUT / "nota_raw.pdf"),
            prefer_css_page_size=True,
            print_background=True,
        )
        b.close()


def norm(x):
    return re.sub(r"\s+", " ", x)


def find_pages():
    d = pymupdf.open(str(OUT / "nota_raw.pdf"))
    texts = [norm(pg.get_text()) for pg in d]
    low = [t.lower() for t in texts]  # text-transform:uppercase das etiquetas sai em maiúsculas
    start = next(i for i in range(3, len(d)) if "nesta secção" in low[i])
    abre = {i for i in range(len(d)) if "nesta secção" in low[i] or ("secção" in low[i] and len(low[i]) < 900)}
    res = {}
    cur = start
    for i, (lv, t) in enumerate(heads):
        key = norm(t)[:20]
        key2 = norm(re.sub(r"^\d+ ", "", t))[:32]
        for pgi in range(cur, len(d)):
            if lv == 3 and pgi in abre:
                continue
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


NPAG = "100"
render(None)
NPAG = str(len(pymupdf.open(str(OUT / "nota_raw.pdf"))))  # nº real de páginas na capa
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


def _ttf(nome):
    """Plex em TTF (o pymupdf não lê woff2); converte uma vez para a cache."""
    dst = OUT / "fontes" / f"{nome}.ttf"
    if not dst.exists():
        from fontTools.ttLib import TTFont

        dst.parent.mkdir(exist_ok=True)
        f = TTFont(str(Path(A).parent / "fonts" / f"{nome}.woff2"))
        f.flavor = None
        f.save(str(dst))
    return str(dst)


F_MONO = _ttf("ibm-plex-mono-500")
INK = (0.063, 0.129, 0.173)
HEX = {"1": "E0A033", "2": "3F9C80", "3": "19A06B", "4": "D9642B", "5": "6F9BE0", "": "9AA8A2"}


def _rgb(hx):
    return tuple(int(hx[k : k + 2], 16) / 255 for k in (0, 2, 4))


txt_pg = [norm(p.get_text()) for p in d]
abre_pg = {i for i, t in enumerate(txt_pg) if "nesta secção" in t.lower() or ("secção" in t.lower() and len(t) < 900)}
first = min(pages.values()) - 1  # abertura da secção 1
sec_idx = [k for k, (lv, _) in enumerate(heads) if lv == 2]
for i in range(first, n):
    if i in abre_pg:
        continue
    pg = d[i]
    w, h = pg.rect.width, pg.rect.height
    kk = max((k for k in sec_idx if pages[k] - 1 <= i), default=sec_idx[0])
    ks = max((k for k in range(kk + 1, len(heads)) if heads[k][0] == 3 and pages[k] - 1 <= i), default=None)
    mm = re.match(r"^(\d+)\s+(.*)$", heads[kk][1])
    num, nome = (mm.group(1), mm.group(2)) if mm else ("", heads[kk][1])
    cor = _rgb(HEX.get(num, HEX[""]))
    ms = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", heads[ks][1]) if ks is not None else None
    trail = f"{num} {nome}".strip().upper() + (f"  ·  {ms.group(1)} {ms.group(2)}".upper() if ms else "")
    trail = trail if len(trail) <= 78 else trail[:77] + "…"
    # aba lateral colorida com a secção
    pg.draw_rect(pymupdf.Rect(w - 15, 70, w, 70 + 135), color=None, fill=cor)
    pg.insert_text(
        (w - 4.2, 70 + 128), f"{num + '  ' if num else ''}{nome}".upper(), fontname="pxm", fontfile=F_MONO,
        fontsize=7.4, color=(0.04, 0.12, 0.17) if num in ("1", "2", "3", "") else (1, 1, 1), rotate=90,
    )
    pg.draw_line((62, h - 44), (w - 62, h - 44), color=INK, width=0.6)
    pg.insert_text((62, h - 31), "PORTO VERDE · NOTA 02  ·  " + trail, fontname="pxm", fontfile=F_MONO, fontsize=6.4, color=(0.34, 0.41, 0.48))
    num_pg = f"{i + 1}"
    pg.insert_text((w - 62 - 4.6 * len(num_pg), h - 30), num_pg, fontname="pxm", fontfile=F_MONO, fontsize=8.6, color=INK)
d.save(str(OUT / "nota_v27.pdf"), garbage=3, deflate=True)
print(n, "páginas")
(OUT / "pv").mkdir(exist_ok=True)
for k in (0, 1, 2, 3, 4):
    d[k].get_pixmap(dpi=55).save(str(OUT / "pv" / f"n{k + 1}.png"))
