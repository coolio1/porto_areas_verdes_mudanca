"""Template «Atlas» (Porto Verde): markdown + nota.json -> PDF A4 com capa, índice, aberturas de secção,
camada «Ler primeiro», abas laterais e rodapé.

Uso:  python build.py [--md exemplo.md] [--cfg nota.json]
Env:  PDF_OUT  pasta de saída (por omissão, esta; escrever no OneDrive com Python pode falhar: usar a scratchpad e cp)
      PW_CHROME  executável do Chromium, se o do playwright não casar com a cache
Requer: pandoc, playwright, pymupdf, beautifulsoup4, fonttools.
Fontes IBM Plex: ../../assets/fonts (o nota.css aponta lá com caminho absoluto; ajustar se o template sair do repo).
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

SP = Path(__file__).parent
ap = argparse.ArgumentParser()
ap.add_argument("--md", default="exemplo.md")
ap.add_argument("--cfg", default="nota.json")
args = ap.parse_args()
CFG = json.loads((SP / args.cfg).read_text(encoding="utf-8"))
OUT = Path(os.environ.get("PDF_OUT") or SP / "saida")
OUT.mkdir(parents=True, exist_ok=True)
FONTS = SP.parent.parent / "assets" / "fonts"
rest = (SP / args.md).read_text(encoding="utf-8")

CORES = CFG.get("cores") or ["E0A033", "3F9C80", "19A06B", "D9642B", "6F9BE0"]
CINZA = "9AA8A2"
MARCA, ETIQ = CFG.get("marca", "Porto Verde"), CFG.get("etiqueta", "Nota")


def cor_de(num):
    return "#" + (CORES[(int(num) - 1) % len(CORES)] if num else CINZA)


heads = [(len(m.group(1)), m.group(2).strip()) for m in re.finditer(r"^(##|###) (.+)$", rest, re.MULTILINE)]
secs = [t for lv, t in heads if lv == 2]


def tiles():
    out = []
    for t in secs:
        m = re.match(r"^(\d+)\s+(.*)$", t)
        n, nome = (m.group(1), m.group(2)) if m else ("", t)
        out.append(f'<div class="tile" style="--c:{cor_de(n)}"><span class="lab">{n.zfill(2) if n else "06"}</span><b>{nome}</b></div>')
    return "".join(out)


def capa():
    c = CFG
    img = ""
    if c.get("imagem"):
        img = (f'<div class="fig"><img src="{(SP / c["imagem"]).as_posix()}">'
               f'<span class="lab">{c.get("legenda_imagem", "")}</span></div>')
    nums = ""
    if c.get("numeros"):
        a, b = c["numeros"][:2]
        nums = (f'<div class="nums"><div><b class="a">{a[0]}</b><span class="lab">{a[1]}</span></div>'
                f'<div><b>{b[0]}</b><span class="lab">{b[1]}</span></div></div>')
    return f"""
<div class="capa"><div class="gr"></div><div class="in">
<div class="cab"><span class="marca"><i></i>{MARCA}</span><span class="lab">{c.get("cabecalho", "")}</span></div>
<div style="display:flex;flex-direction:column;gap:3mm;margin-top:2mm"><span class="lab" style="color:#E0A033">{c.get("kicker", "")}</span>
<h1>{c["titulo"]}</h1><p class="sub">{c.get("subtitulo", "")}</p></div>
{img}{nums}
<div class="dossier"><span class="lab" style="opacity:.8">Neste dossier</span><div class="tiles">{tiles()}</div></div>
<p class="aviso">{c.get("aviso", "")} __NPAG__ páginas.</p>
</div></div>

"""


def toc_html(pages):
    out = ['<div class="toc"><h2>Índice</h2><ul>']
    for i, (lv, t) in enumerate(heads):
        p = pages.get(i, "") if pages else ""
        mm = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", t)
        num, txt = (mm.group(1), mm.group(2)) if mm else ("", t)
        if lv == 2 and num:
            num += "."
        out.append(f'<li class="n{lv}"><a href="#sec{i}"><span class="tn">{num}</span>'
                   f'<span class="t">{txt}</span><span class="d"></span><span class="p">{p}</span></a></li>')
    out.append("</ul></div>\n\n")
    return "\n".join(out)


def painel_ler(num):
    """«Ler primeiro»: só texto e números extraídos da secção (nota.json -> ler)."""
    d = (CFG.get("ler") or {}).get(num)
    if not d:
        return ""
    nm = "".join(f'<div class="nm"><b>{a}</b><span>{b}</span></div>' for a, b in d["numeros"])
    return (f'<div class="lp"><span class="lab">Ler primeiro · em resumo</span><div class="res">{d["resumo"]}</div>'
            f'<div class="nums">{nm}</div>'
            f'<div class="nota">Camada de leitura: texto e números extraídos da secção; não é conteúdo novo</div></div>')


def abertura(i, pages):
    t = heads[i][1]
    mm = re.match(r"^(\d+)\s+(.*)$", t)
    num, txt = (mm.group(1), mm.group(2)) if mm else ("", t)
    subs = []
    for k in range(i + 1, len(heads)):
        if heads[k][0] == 2:
            break
        m3 = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", heads[k][1])
        if m3:
            subs.append((m3.group(1), m3.group(2), pages.get(k, "") if pages else ""))
    lis = "".join(f'<li><span class="tn">{a}</span><span class="tt">{b}</span><span class="pp">{c}</span></li>'
                  for a, b, c in subs)
    cls = "sub dois" if len(subs) > 9 else "sub"
    bloco = f'<div class="{cls}"><span class="lab">Nesta secção</span><ul>{lis}</ul></div>' if subs else ""
    return (f'::: {{.abertura style="--c:{cor_de(num)}"}}\n'
            f'<div class="gr"></div><div class="in"><div class="cab"><span class="lab">{MARCA} · {ETIQ}</span>'
            f'<span class="lab">Secção {num or "—"}</span></div>'
            f'<div class="n">{num or "·"}</div><div class="t">{txt}</div>{painel_ler(num)}{bloco}</div>\n:::\n\n')


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


def nohyphen(path):
    """Palavras com hífen não se partem ao fim da linha (excepto URLs); número e unidade ficam juntos."""
    from bs4 import BeautifulSoup, NavigableString

    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    # o pandoc só envolve o título da secção: a abertura passa a irmã da sua secção (senão rebenta a paginação)
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
    pat1 = re.compile(r"(?<!\S)[^\W_]+(?:-[^\W_]+)+(?=[\s,;:)]|$)")
    for node in list(soup.find_all(string=True)):
        if node.parent.name in ("script", "style", "a", "code"):
            continue
        pat = pat1 if node.find_parent(id="referências") else pat0
        txt = str(node)
        if "-" not in txt or not pat.search(txt):
            continue
        frag = BeautifulSoup("", "html.parser")
        pos, out = 0, []
        for m in pat.finditer(txt):
            out.append(NavigableString(txt[pos: m.start()]))
            sp = frag.new_tag("span", attrs={"class": "nq"})
            sp.string = m.group(0)
            out.append(sp)
            pos = m.end()
        out.append(NavigableString(txt[pos:]))
        node.replace_with(*out)
    path.write_text(str(soup).replace(" viewbox=", " viewBox="), encoding="utf-8")  # html.parser baixa a caixa


def render(pages):
    (OUT / "nota2.md").write_text(
        f"% {CFG['titulo']}\n% {MARCA}\n" + capa().replace("__NPAG__", NPAG) + toc_html(pages) + ids_titulos(rest, pages),
        encoding="utf-8")
    subprocess.run(["pandoc", str(OUT / "nota2.md"), "-s", "--section-divs", "--css", str(SP / "nota.css"),
                    "--embed-resources", "-f", "markdown+pipe_tables+fenced_divs", "-V", "lang=pt-PT",
                    "-o", str(OUT / "nota.html")], check=True)
    nohyphen(OUT / "nota.html")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=os.environ.get("PW_CHROME") or None)
        pg = b.new_page()
        pg.goto((OUT / "nota.html").as_uri())
        pg.pdf(path=str(OUT / "nota_raw.pdf"), prefer_css_page_size=True, print_background=True)
        b.close()


def norm(x):
    return re.sub(r"\s+", " ", x)


def escura(pg):
    """Abertura/capa = página de fundo escuro (canto sem texto); robusto a texto que cite «secção»."""
    px = pg.get_pixmap(dpi=30, clip=pymupdf.Rect(2, 2, 30, 30))
    return sum(px.pixel(0, 0)[:3]) < 200


def find_pages():
    d = pymupdf.open(str(OUT / "nota_raw.pdf"))
    texts = [norm(pg.get_text()) for pg in d]
    low = [t.lower() for t in texts]  # as etiquetas em maiúsculas saem em maiúsculas
    abre = {i for i in range(len(d)) if escura(d[i])}
    cur = next(i for i in range(2, len(d)) if i in abre)
    res = {}
    for i, (lv, t) in enumerate(heads):
        key, key2 = norm(t)[:20], norm(re.sub(r"^\d+ ", "", t))[:32]
        for pgi in range(cur, len(d)):
            if lv == 3 and pgi in abre:
                continue
            if (key2 in re.sub(r"[\d\x00]", "", texts[pgi])) if lv == 2 else (key in texts[pgi]):
                res[i], cur = pgi + 1, pgi
                break
        else:
            raise SystemExit(f"título não encontrado: {t}")
    return res, d


NPAG = "100"
render(None)
NPAG = str(len(pymupdf.open(str(OUT / "nota_raw.pdf"))))
render(None)
pages, d = find_pages()
d.close()
render(pages)
pages2, d = find_pages()
assert pages2 == pages, "índice mudou entre passagens"

# ---------- marcadores, abas e rodapé ----------
d.set_toc([[lv - 1, re.sub(r"^(\d+) ", r"\1. ", t) if lv == 2 else t, pages[i]] for i, (lv, t) in enumerate(heads)])
n = len(d)


def _ttf(nome):
    dst = OUT / "fontes" / f"{nome}.ttf"
    if not dst.exists():
        from fontTools.ttLib import TTFont

        dst.parent.mkdir(exist_ok=True)
        f = TTFont(str(FONTS / f"{nome}.woff2"))
        f.flavor = None
        f.save(str(dst))
    return str(dst)


F_MONO = _ttf("ibm-plex-mono-500")
INK = (0.063, 0.129, 0.173)


def _rgb(hx):
    hx = hx.lstrip("#")
    return tuple(int(hx[k: k + 2], 16) / 255 for k in (0, 2, 4))


txt_pg = [norm(p.get_text()) for p in d]
abre_pg = {i for i in range(len(d)) if escura(d[i])}
first = min(pages.values()) - 1
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
    cor = _rgb(cor_de(num))
    ms = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", heads[ks][1]) if ks is not None else None
    trail = f"{num} {nome}".strip().upper() + (f"  ·  {ms.group(1)} {ms.group(2)}".upper() if ms else "")
    trail = trail if len(trail) <= 78 else trail[:77] + "…"
    pg.draw_rect(pymupdf.Rect(w - 15, 70, w, 205), color=None, fill=cor)
    claro = (not num) or (int(num) - 1) % len(CORES) in (0, 1, 2)
    pg.insert_text((w - 4.2, 198), f"{num + '  ' if num else ''}{nome}".upper(), fontname="pxm", fontfile=F_MONO,
                   fontsize=7.4, color=(0.04, 0.12, 0.17) if claro else (1, 1, 1), rotate=90)
    pg.draw_line((62, h - 44), (w - 62, h - 44), color=INK, width=0.6)
    pg.insert_text((62, h - 31), f"{MARCA} · {ETIQ}  ·  ".upper() + trail, fontname="pxm", fontfile=F_MONO,
                   fontsize=6.4, color=(0.34, 0.41, 0.48))
    s = f"{i + 1}"
    pg.insert_text((w - 62 - 4.6 * len(s), h - 30), s, fontname="pxm", fontfile=F_MONO, fontsize=8.6, color=INK)
destino = OUT / CFG.get("saida", "nota.pdf")
d.save(str(destino), garbage=3, deflate=True)
print(n, "páginas ->", destino)
