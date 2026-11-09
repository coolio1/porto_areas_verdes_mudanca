r"""Gera nota.factos.propostas.md (propostas com excerto literal do armazém Fontes) e nota.factos.pendentes.md.

Uso: python -I -X utf8 construir_factos.py          (a partir de qualquer pasta)
Entradas: nota.md; texto das obras no armazém Fontes\AI habitacao\<slug(chave)>\texto.txt. A chave de cada [n] é o
          DOI ou o URL (web_xxx) da própria entrada [n] das Fontes (sem mapa à parte).
Saídas:   nota.factos.propostas.md  (uma linha por valor e [n]: excerto literal com o valor; marcada «(auto)» até alguém
          ler; NUNCA sobrepõe nota.factos.md, que tem linhas revistas à mão: copiar daqui só o que se aprova)
          nota.factos.pendentes.md (números sem [n], com [n] sem texto local, ou com o valor ausente do texto citado)
Uma linha (auto) prova que o valor está no texto da fonte; que a frase APOIA a afirmação da nota é leitura humana
ou da revisão independente (research.md Passo 3.7), não deste script.
"""

import importlib.util
import re
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent
ARM = Path(r"C:\Users\quent\OneDrive\Claude\Fontes\AI habitacao")
sp =importlib.util.spec_from_file_location("rf", Path.home() / ".claude" / "scripts" / "research_fetch.py")
rf = importlib.util.module_from_spec(sp)
sp.loader.exec_module(rf)


def plano(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def palavras(s):
    return {w for w in re.findall(r"[a-z]{5,}", plano(s))}


_cache = {}


def corpus(f):
    """(texto com espaços colapsados, {valor arredondado: [posições]})."""
    if f not in _cache:
        bruto = (ARM / rf.slug(f) / "texto.txt").read_text(encoding="utf-8", errors="replace")
        txt = re.sub(r"\s+", " ", re.sub(r"-\s*\n\s*", "", bruto))
        idx = {}
        for m in rf._NUM.finditer(txt):
            for v in rf._vals(m.group(0)):
                idx.setdefault(round(v, 6), []).append((m.start(), m.end()))
        _cache[f] = (txt, idx)
    return _cache[f]


RUIDO = re.compile(r"https?://|doi\.org|issn|hdl\.handle|isbn|\bpp\.|\bvol\.", re.IGNORECASE)


def janela_boa(ex):
    pal = re.findall(r"\S+", ex)
    dig = sum(1 for w in pal if re.search(r"\d", w))
    return len(pal) >= 6 and dig / len(pal) <= 0.3 and not RUIDO.search(ex)


def janela(txt, ini, fim):
    """Excerto literal (6–40 palavras) em volta de txt[ini:fim], sem aspas rectas nem barras verticais."""
    if ini > 0 and (txt[ini - 1].isalpha() or txt[ini - 1] == "."):
        return None  # nota de rodapé colada à palavra («…uninformative.17»)
    for raio in (160, 110, 70, 45):
        a, b = max(0, ini - raio), min(len(txt), fim + raio)
        # alinhar a fronteiras de palavra
        a = txt.rfind(" ", 0, a + 1) + 1 if a > 0 else 0
        b = txt.find(" ", b) if txt.find(" ", b) != -1 else len(txt)
        ex = txt[a:b].strip()
        if '"' not in ex and "|" not in ex and janela_boa(ex):
            return ex
    return None


def melhor_excerto(valores, frase_nota, fontes, unidade='', valor_txt=''):
    """(pontuação, ficheiro, excerto) com mais palavras em comum com a frase da nota."""
    alvo = palavras(frase_nota)
    melhor = None
    for f in fontes:
        txt, idx = corpus(f)
        for v in valores:
            for ini, fim in idx.get(round(v, 6), [])[:40]:
                ex = janela(txt, ini, fim)
                if not ex:
                    continue
                if not any(rf._igual(a, b) for t2 in rf._tokens(ex) for a in rf._vals(t2) for b in valores):
                    continue
                if valor_txt and not rf._unidade_ok(valor_txt, ex):
                    continue  # unidade ou escala diferentes («7,9 M€» não prova «7,9 mil M€»)
                pal = palavras(ex)
                pont = len(alvo & pal) / max(1, min(len(alvo), 12))
                if unidade and re.search(r"[\d.,]\s?" + unidade, ex):
                    pont += 0.5
                if melhor is None or pont > melhor[0]:
                    melhor = (pont, f, ex)
    return melhor


def frase_da_nota(linha, tok):
    pos = linha.find(tok)
    ini = max(linha.rfind(". ", 0, pos), linha.rfind("| ", 0, pos)) + 1
    fim = linha.find(". ", pos)
    return linha[ini : fim if fim != -1 else len(linha)].strip(" |")


def main():
    nota = (BASE / "nota.md").read_text(encoding="utf-8")
    mapa = {}  # [n] -> chave (DOI ou web_xxx da entrada) com texto no armazém
    for n, entrada in rf._entradas_fontes(nota)[1].items():
        chaves = [d.lower().rstrip(".,;") for d in rf._dois(entrada)] + [
            rf.chave_web(u.rstrip(".,;"))
            for u in re.findall(r"https?://[^\s)>\]]+", entrada)
            if not rf.DOI_RE.search(u)
        ]
        ok = next((k for k in chaves if (ARM / rf.slug(k) / "texto.txt").exists()), None)
        if ok:
            mapa[n] = ok
    cit = rf._citacoes_por_linha(nota)
    linhas = rf._linhas_de_corpo(nota)
    factos, chave, pend = [], {}, []
    for n, ln in linhas:
        cs = cit.get(n, set())
        for tok in rf._tokens(ln):
            vs = rf._vals(tok)
            if not vs:
                continue
            ja = [fa for c in cs for v in vs if (c, round(v, 6)) in chave for fa in [chave[(c, round(v, 6))]]]
            if ja:
                continue
            fontes = {c: mapa[c] for c in sorted(cs) if c in mapa}
            frase = frase_da_nota(ln, tok)
            if not cs:
                pend.append((n, tok, "sem [n] no parágrafo (cálculo próprio, cabeçalho ou falta citação)", frase))
                continue
            if not fontes:
                pend.append((n, tok, f"[{', '.join(map(str, sorted(cs)))}] sem texto local", frase))
                continue
            apos = ln[ln.find(tok) + len(tok) :].lstrip(" \u00a0")[:12].lower()
            unidade = "(?:%|per ?cent|percent)" if apos.startswith("%") else (
                "(?:p\\.p\\.|percentage points?|pontos? percentuais?)" if apos.startswith(("p.p", "pontos")) else ""
            )
            um = re.match(
                r"^\s?(?:mil milhões de euros|milhões de euros|mil milhões|milhões|mil M€|M€|pontos percentuais|p\.p\.|%|€|euros)",
                ln[ln.find(tok) + len(tok) :],
            )
            valor_txt = tok + (um.group(0) if um else "")
            m = melhor_excerto(vs, frase, list(fontes.values()), unidade, valor_txt)
            if not m:
                pend.append((n, tok, f"valor ausente do texto de [{', '.join(map(str, sorted(fontes)))}]", frase))
                continue
            pont, f, ex = m
            c = next(k for k, v in fontes.items() if v == f)
            fid = f"F{len(factos) + 1}"
            grandeza = " ".join(frase.split()[:8]) + (" …" if len(frase.split()) > 8 else "")
            grandeza = grandeza.replace("|", "/")
            marca = "(auto)" if pont >= 0.5 else "(auto, REVISAR: unidade ou contexto fracos)"
            factos.append(
                f'{fid} | {marca} {grandeza} | {valor_txt} | — | — | — | [{c}] | excerto: "{ex}" [{f}]'
            )
            for v in vs:
                chave[(c, round(v, 6))] = fid
    cab = "# factos (G19) — gerado por construir_factos.py; linhas (auto) = valor presente na fonte, apoio por confirmar\n"
    (BASE / "nota.factos.propostas.md").write_text(cab + "\n".join(factos) + "\n", encoding="utf-8")
    pt = "# pendentes do factos.md\n\nn.º da linha | número | motivo | frase\n" + "\n".join(
        f"{n} | {tok} | {mot} | {fr[:140]}" for n, tok, mot, fr in pend
    )
    (BASE / "nota.factos.pendentes.md").write_text(pt + "\n", encoding="utf-8")
    rev = sum(1 for x in factos if "REVISAR" in x)
    print(f"{len(factos)} linhas auto ({rev} a rever); {len(pend)} pendentes")


if __name__ == "__main__":
    main()
