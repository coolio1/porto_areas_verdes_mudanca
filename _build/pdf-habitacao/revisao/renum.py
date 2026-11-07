"""Renumera as referencias da nota por ordem alfabetica e actualiza as citacoes [n].
Uso: python -X utf8 renum.py nota_r2.md refs_novas_r2.md nota_r3.md mapa.json
"""

import re, sys, json, unicodedata

src, novas, out, mapa_out = sys.argv[1:5]
t = open(src, encoding="utf-8", newline="").read()
eol = "\r\n" if "\r\n" in t else "\n"
i = t.index("## Referências")
body, tail = t[:i], t[i:]
head, _, lista = tail.partition("\n")
lista = lista.replace("\r\n", "\n")

entradas = {}
ordem = []
for linha in lista.split(chr(10)):
    if not linha.strip():
        continue
    m = re.match(r"(\d+)\. (.*)", linha)
    assert m, linha[:80]
    n = int(m.group(1))
    entradas[n] = m.group(2).strip()
    ordem.append(n)
assert ordem == list(range(1, len(ordem) + 1)), "lista nao sequencial"

# novas referencias: linhas «[NOVA-xx] texto»
for linha in open(novas, encoding="utf-8"):
    m = re.match(r"\[(NOVA-[A-Z0-9]+)\] (.*)", linha.strip())
    if m:
        entradas[m.group(1)] = m.group(2).strip()
usadas = set(re.findall(r"\[(NOVA-[A-Z0-9]+)\]", body))
assert usadas <= set(entradas), usadas - set(entradas)


def chave(txt):
    s = re.sub(r"^[\*\s]+", "", txt)
    s = re.sub(r"^(The|Les|Le|La|Die|Der|Das)\s+", "", s, flags=re.I)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^0-9A-Za-z ]+", " ", s).lower()
    return re.sub(r"\s+", " ", s).strip()


ids = list(entradas)
ids.sort(key=lambda k: (chave(entradas[k]), str(k)))
mapa = {str(k): n for n, k in enumerate(ids, 1)}


# citacoes: [n] e [NOVA-xx]
def troca(m):
    k = m.group(1)
    assert k in mapa, k
    return "[%d]" % mapa[k]


novo_body = re.sub(r"\[(\d+|NOVA-[A-Z0-9]+)\]", troca, body)
linhas = [f"{mapa[str(k)]}. {entradas[k]}" for k in ids]
novo = novo_body + head + "\n\n" + "\n\n".join(linhas) + "\n"
if eol == "\r\n":
    novo = novo.replace("\r\n", "\n").replace("\n", "\r\n")
open(out, "w", encoding="utf-8", newline="").write(novo)
json.dump(mapa, open(mapa_out, "w"), indent=0)
print("refs", len(ids), "citacoes trocadas", len(re.findall(r"\[\d+\]", novo_body)))
