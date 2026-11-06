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
