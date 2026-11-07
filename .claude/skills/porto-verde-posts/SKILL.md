---
name: porto-verde-posts
description: Protocolo de Porto Verde para criar artigos (_posts/) e thumbnails dos cards do index (capture_cards.py). Usar ao adicionar/editar artigos ou cards do site.
---

## Cards do index — protocolo de thumbnails

Cada card de mapa no `index.html` tem um thumbnail (`<img class="card-thumb">`) capturado automaticamente via Playwright a partir do GitHub Pages.

### Quando regenerar
- Ao adicionar um novo card ao `index.html`
- Ao alterar significativamente o aspecto visual de um mapa existente

### Como capturar
```bash
python capture_cards.py
```
- Requer Playwright Chromium: `python -m playwright install chromium` (só uma vez)
- Abre cada URL do GitHub Pages em headless, aguarda tiles Leaflet, faz screenshot do `#map`
- Guarda em `assets/images/cards/<slug>.jpg` (600×340px, JPEG Q88)

### Ao adicionar um novo card
1. Adicionar entrada em `MAPS` em `capture_cards.py` com `slug`, `url` e `wait_for`
2. Correr `python capture_cards.py` (só o novo slug é gerado; os existentes são substituídos se já existirem)
3. No `index.html`, usar `<img src="{{ site.baseurl }}/assets/images/cards/<slug>.jpg" class="card-thumb" style="object-position:center center" alt="...">`
4. Commit incluindo a imagem nova e o `index.html`

## Artigos (`_posts/`) — protocolo de criação

### Passos obrigatórios

1. **Assets primeiro** — copiar para as pastas correctas antes de escrever o Markdown:
   - Imagens → `assets/images/<slug>-<descricao>.jpg`
   - PDFs → `assets/pdfs/<nome>-<ano>.pdf`
   - Áudio → **nunca no repositório** se >25 MB (limite GitHub Pages); alojar externamente e usar link directo ou `<audio src="...">`.

2. **Criar `_posts/YYYY-MM-DD-slug.md`** com front matter obrigatório:
   ```yaml
   ---
   layout: post
   title: "Título em PT-PT"
   description: "Descrição de 1-2 frases para SEO e card do índice."
   date: YYYY-MM-DD
   tags: [tag1, tag2, ...]
   ---
   ```

3. **Links internos** — sempre com prefixo `{{ site.baseurl }}/`:
   - Imagens: `![alt]({{ site.baseurl }}/assets/images/ficheiro.jpg)`
   - PDFs: `[texto]({{ site.baseurl }}/assets/pdfs/ficheiro.pdf)`
   - Legendas de imagem: linha em itálico imediatamente após o `![]()`.

4. **Índice automático** — o `index.html` usa `{% for post in site.posts %}` e lista todos os posts automaticamente. **Nunca editar `index.html`** para adicionar artigos.

5. **Commit e push** — incluir assets e ficheiro `.md` no mesmo commit.

### Regras de formatação

- `##` para secções principais, `###` para subsecções.
- Espaçamento antes de títulos gerido pelo CSS (`_layouts/default.html`): `article h2 { margin-top: 2.5rem }`. **Não usar `&nbsp;`**.
- Listas com bullet points (`-`) para enumerações dentro de secções.
- Emails como `[addr](mailto:addr)`; URLs externas como `[texto](url)`.
- Referências bibliográficas no final, ordenadas alfabeticamente (em artigos científicos).
- Acentuação PT-PT correcta em todo o texto.

## Artigos científicos com «nota completa» em PDF (aprendido em 2026-11-07, post habitação)

### Texto e fontes
- **Resultado de /research que alimenta um artigo:** propor logo a integração substantiva (secção nova por conclusão principal, incluindo o que falhou e o que é só promessa), não só correcções e uma linha; mostrar o texto ao utilizador antes de gravar. O utilizador reagiu a uma 1.ª proposta curta («depois de tanta investigação só mudas isso?»).
- **Cada número do texto novo** tem de ter fonte lida (excerto confirmado) ou levar a ressalva no texto («segundo a imprensa», «só vista em resumo», «working paper sem revisão por pares»). Conferir **o que a medida é** antes de a nomear (o «zonamento de 2018» que baixou 8 % era a restrição ao AL por bairro, não zonamento de construção).
- **Texto-fonte da nota sem instruções soltas:** procurar «a acrescentar», «a substituir», «TODO» antes de construir o PDF (a tabela 4.1 e a página 41 saíram partidas por isto).
- **Título, descrição (front matter) e capa do PDF** dizem o mesmo; mudar o título não muda o nome do ficheiro do post (o endereço mantém-se).

### Construção do PDF (pandoc + Chromium, `mkpdf.py`)
- Versão nova = nome novo (`nota_vNN.pdf`); copiar para `assets/pdfs/<slug>-nota-completa-<ano>.pdf`. **Nunca correr o script de publicação (`publicar`)**: dar ao utilizador o comando `! python ~/.claude/scripts/publicar.py porto-verde --permitir <pdf>` e confirmar depois o hash no site.
- Ao acrescentar secções, actualizar o número de páginas da capa (`NPAG`, escrito à mão).
- **Não substituir os ids automáticos dos títulos** (`{#id}`): o CSS usa-os (`#referências`, `#recomendações`) e o PDF encolheu de 57 para 32 páginas. Para âncoras do índice usar `<span id="secN"></span>` dentro do título.
- Índice clicável (`<a href="#secN">` por entrada), número numa coluna própria (`.tn`) e título com recuo; títulos de nível 2 numerados levam ponto («1. Introdução»).
- Referências em 2 colunas: o recuo da lista tem de caber números de 3 algarismos (`padding-left:2.7em`); com menos, o 1.º dígito fica cortado («33.» em vez de «233.»).
- **Verificar sempre, renderizando as páginas** (`pymupdf` → PNG, ver capa, índice, páginas com tabelas e a última das referências): n.º de páginas, nenhuma quase vazia, nenhuma linha a acabar em hífen fora de URLs, nenhum `%` separado do número, sequência das referências sem cortes.
