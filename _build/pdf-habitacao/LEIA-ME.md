# Construção do PDF «Nota completa» (habitação Lisboa e Porto)

Cópia durável dos scripts que estavam no scratchpad (2026-11-07). A pasta `_build` não é publicada pelo Jekyll (começa por `_`).

- `nota.md` — texto da nota (fonte do PDF; copiar a versão final antes de reconstruir).
- `mkpdf.py` — pandoc → HTML → Chromium (playwright) → pymupdf; escreve `nota_v26.pdf`. `SP` é a pasta do script; `NPAG` tem de ser posto à mão com o n.º de páginas final.
- `nota.css` — estilo (corpo a duas colunas; `.conc` = página Conclusões, A4 fixa).
- `modelo/conclusoes.py` — texto da página Conclusões; `gen_include.py` gera `_includes/conclusoes-habitacao.html` do post.
- `revisao/renum.py` — junta as referências novas e renumera `[n]` por ordem alfabética.
- Regras aprendidas: linha em branco antes de `## Referências` (senão o Chromium encolhe o PDF todo); conferir páginas e fim de linha com hífen (só URLs); páginas e Conclusões numa folha A4.
- Lições da ronda 3 (2026-11-08): depois de mexer em texto, `NPAG` em `mkpdf.py` = nº final de páginas (reconstruir 2 vezes) e **ver a imagem** da página Conclusões (o texto que cresce sobrepõe o rodapé; ajustar `.conc .pacote`, `.passos` ou encurtar); identificadores com hífen nas referências (ex.: «758-B/2024») levam `<span class="nq">`; editar com Python e U+00A0 literais, nunca `re.sub` com `` (corrompeu algarismos); a lista de referências lê-se linha a linha; resoluções de facto só entram depois de verificadas contra a fonte.
- Pré-requisitos: pandoc, playwright (Chromium), pymupdf, beautifulsoup4.
