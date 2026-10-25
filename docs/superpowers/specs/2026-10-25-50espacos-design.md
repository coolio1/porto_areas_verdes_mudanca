# Campanha 50 espaços verdes no Porto Verde — design

*2026-10-25. Estado: rascunho para aprovação. Nada foi construído.*

## Intenção

Trazer a campanha «50 espaços verdes em perigo e a preservar» (Campo Aberto, 2006–2009, continuada até hoje) para o Porto Verde, como memória histórica, registo do estado actual de cada espaço e catálogo consultável dos espaços. O Porto Verde passa a ser a casa digital da campanha, hoje dispersa por um site Webnode, um PDF de 2016 e arquivos em disco.

## Objectivos

- Secção própria `/50espacos/` com narrativa da campanha, metodologia, imprensa e uma página por espaço (111 espaços, 9 concelhos originais da AMP).
- Cada espaço com texto único em que as informações de 2006–2008, 2014–2015 e a mais recente (Webnode) estão fundidas, com as datas na própria frase.
- Indicar quais são os 50 seleccionados. Não há ordem de importância: ver «Correcção de 2026-10-25».
- Mapa de pontos aproximados, só onde existam coordenadas, com a origem indicada.
- Estado actual por fases, começando pelo Porto, com data de verificação.

## Não-objectivos

- Polígonos dos espaços. Só mais tarde e só do PDM ou do OSM (regra do projecto: nunca derivar nem inventar geometrias).
- Os concelhos que aderiram à AMP depois de 2006 (Arouca, Oliveira de Azeméis, Paredes, Santa Maria da Feira, Santo Tirso, São João da Madeira, Trofa, Vale de Cambra): têm páginas no Webnode mas não fizeram parte da campanha de 2006–2009. Ficam fora desta fase (decisão a confirmar, ver «Pendente»).
- Reescrever a narrativa da campanha como peça jornalística nova.
- Votação electrónica, formulários e plataforma de parcerias.

## Anti-objectivos (falharia mesmo que funcionasse)

- Publicar dados pessoais: contactos de proponentes, inscrições do almoço biológico, lista do grupo de trabalho, pontuações individuais dos grupos de avaliação.
- Inventar, aproximar ou «limpar» factos ao fundir as camadas de texto, ou misturar informação de 2006 com a de 2019 sem a datar.
- Editar HTML ou Markdown das fichas à mão (regra do projecto: cada script gera o seu HTML).

## Fontes (4) e hierarquia

| Fonte | Conteúdo | Data |
|---|---|---|
| Zip `Site Campanha 50 espacos verdes` | Site original da campanha: descrição, calendário, balanço, comunicados, revista de imprensa (35 PDFs), fichas dos espaços com fotos e anexos | 2006–2009 |
| Pasta `Projectos\Campanha 50 espacos` | Documentação interna: processo de selecção, resultados de 2009 (`SeleccaoEV.xlsx`), fichas «NQ», apresentações, folheto, textos | 2006–2009 |
| `111espacos-TOTAL.pdf` (campoaberto.pt, 2016; ligado do Webnode como «compilação») | As 111 fichas, com as camadas de 2006–2008 (fundo branco) e actualizações de 2014–2015 (verde: entidades oficiais; azul: Campo Aberto; amarelo: cidadãos e associações; salmão: destaques de última hora). Seleccionados primeiro, restantes em anexo | 2014–2016 |
| Webnode `espacosvivos-grporto-amp.webnode.pt` | Narrativa de 2017 em diante, uma página por concelho, «Últimos espaços livres no Porto» (7 seleccionados e 16 não seleccionados), coordenadas WGS84 (2 casas decimais), proponente, área, estado actualizado (Parque Oriental até 2019) | 2017–hoje |

**Hierarquia por camada, não por fonte:** 2006–2008 (zip e projecto; as fichas comuns têm a mesma data interna e texto praticamente idêntico) → 2014–2015 (PDF) → Webnode (o mais recente). Onde divergirem, vale a mais recente, mas a divergência é registada numa tabela e mostrada antes de publicar.

**Número canónico:** 111 espaços (os 113 originais menos 2 que não cumpriam os critérios, segundo o PDF). Imprensa de 2007–2008 fala de 115 e 113, e o site do zip de «mais de 70», por serem fotografias de momentos anteriores: a narrativa deve datar cada número.

## Decisões do utilizador

1. Objectivo: mistura de memória histórica, retomar a campanha (estado actual) e base de dados dos espaços.
2. Território: todo o Grande Porto, tudo (111 espaços).
3. Estrutura: secção própria com uma página por espaço, em colecção Jekyll separada de `_posts/`.
4. Estado actual: publicar já o histórico; verificar por fases, Porto e os 50 primeiro, com data.
5. Merge da narrativa: usar a mais recente (Webnode) como espinha, melhorar com as outras fontes, reescrevendo em PT-PT. Usar as três fontes iniciais (e agora o PDF de 2016).
6. Publicável: fichas e fotos, informação geral e metodologia, imprensa (lista com os PDFs, decisão dele sobre direitos), lista dos 50 e a ordem, sem pontuações individuais. Nada com dados pessoais.
7. Mapa: pontos aproximados só onde exista localização, com a origem indicada.
8. URL: `/50espacos/`.
9. Ficheiros: o utilizador copiou o arquivo para `docs/fonte_campanha/` (no `.gitignore`, fora do Jekyll).
10. Anexos por espaço: fotos, mapas e PDFs de apoio. Ficam fora os `.doc/.docx` originais, `Thumbs.db`, `.mno`, páginas antigas em HTML e duplicados `lista`/`listaf`.
11. Webnode: «Apelo à CMP» e «Últimos espaços livres no Porto» incorporados; «O livro» só como ligação.
12. Navegação: ligação na barra (`nav.py`) e card no index.
13. Texto de cada espaço: **um texto único com as datas na frase** (não três blocos separados). Escolhido pelo utilizador contra a recomendação, que era blocos datados; o custo é reescrever 111 fichas.
14. Fusão: piloto nos 23 do Porto; só depois se decide o resto.

## Estrutura do site

| Página | URL |
|---|---|
| A campanha (história, critérios, metodologia, fases, livro) | `/50espacos/` |
| Campanha na imprensa | `/50espacos/imprensa/` |
| Lista e mapa dos espaços | `/50espacos/espacos/` |
| Um espaço | `/50espacos/espacos/<concelho>/<slug>/` |

Colecção Jekyll `espacos` (`output: true`, `permalink: /50espacos/espacos/:path/`) em `_espacos/<concelho>/<slug>.md`. O slug é legível; o número da ficha de 2006 fica nos dados (a numeração mudou entre versões). Prefixo do site: `baseurl: /porto_areas_verdes_mudanca`.

## Design das páginas (decidido pelo utilizador, 2026-10-25)

Estilo visual: o dos artigos existentes (`_layouts/post.html`, variáveis `--text`, `--muted`, `--green`), responsivo.

- **Ficha de espaço:** migalhas (concelho › espaço); título; etiquetas (seleccionado + posição, estado actual); linha de dados (freguesia, área, proponente); texto fundido; galeria de fotos; mini-mapa aproximado (só com coordenadas); anexos e fontes.
- **Lista e mapa** (`/50espacos/espacos/`): mapa de pontos no topo; lista filtrável por concelho, «só os 50» e estado; clicar num ponto ou linha abre a ficha; espaços sem coordenadas só na lista.
- **Narrativa** (`/50espacos/`): números-chave (111 espaços, 50 seleccionados, 9 concelhos), atalhos para lista/mapa e imprensa, linha do tempo 2006→hoje, metodologia e critérios, ligação ao livro.
- **Imprensa:** lista agrupada por ano, mais recente primeiro; jornal, data, título e ligação directa ao PDF; sem miniaturas.

### Direcção visual: «Dossiê de campo» (escolhida pelo utilizador, método do plugin `frontend-design`)

- **Ideia:** cada espaço é uma ficha de levantamento. A secção vive no ADN do Porto Verde (mesmo verde) mas com identidade própria.
- **Cor (tokens em `:root`, com variante escura em `prefers-color-scheme`):** papel `#F6F7F4`, floresta `#1F4D2B`, verde do site `#2E7D32`, amarelo-sinal `#E8C21A` (só para «seleccionado»), grafite `#23282B`, azul-rio `#2B6C8F` (ligações e mapa).
- **Tipografia:** grotesca sólida para títulos e dados (proposta: Archivo) e serifa de leitura para as narrativas (proposta: Source Serif 4), alojadas no repositório (`assets/fonts/`, sem pedidos a terceiros). Linhas < 80 caracteres; serifa com entrelinha ligeiramente maior.
- **Momento memorável (uma só aposta):** abertura de `/50espacos/` com 111 marcas, 50 preenchidas a amarelo-sinal; cada marca abre a ficha e mostra o nome ao passar o rato ou ao focar. As marcas preenchem-se uma vez ao carregar; sem movimento com `prefers-reduced-motion`. Tudo o resto é sóbrio.
- **Estrutura como informação:** dados da ficha em tabela de caixas com bordas (campo → valor), não em cadeias separadas por pontos; números só onde há sequência real (posição em 2009, linha do tempo).
- **A evitar (clichés listados pelo método):** palavra isolada em cor ou itálico nos títulos, rótulos em maiúsculas, creme com terracota, cartões iguais com a mesma sombra, setas «→» em todas as ligações.
- **Mínimos de qualidade:** legível a 375 px, foco de teclado visível, contraste AA, texto alternativo nas fotos, marcas navegáveis por teclado.

## Modelo de dados de um espaço (front matter)

`titulo`, `concelho`, `freguesia`, `n_ficha` (2006–2008), `seleccionado` (sim/não), `selecao` (`2009-04` ou `posterior`, só para os 50), `proponente` (nome público da ficha original, sem contactos), `area_ha`, `lat`/`lon` + `origem_coord`, `estado_actual` (por verificar | preservado | parcialmente construído | destruído | ameaçado) + `data_verificacao`, `fontes` (lista), `fotos`, `anexos`. Corpo: texto fundido.

## Pipeline (a construir)

Scripts Python descartáveis ou de projecto, sem editar à mão:
1. **Extracção:** `.docx` de 2006–2008 (zip e projecto, reconciliados por slug); texto do PDF de 2016 por espaço; texto e coordenadas do Webnode por concelho.
2. **Reconciliação:** tabela de diferenças (nomes com gralhas, fichas só numa fonte, `lista` contra `listaf`, que têm 59 ficheiros com tamanhos diferentes).
3. **Fusão (editorial):** rascunho de texto único por espaço com datas inline, a rever pelo utilizador. Piloto: Porto (23).
4. **Geração:** `_espacos/**/*.md`, listas por concelho e dados do mapa a partir do front matter.
5. **Cópia de fotos e PDFs** das fontes para `50espacos/` (na raiz do projecto), com redimensionamento das fotos.

## Mapa

Marcadores simples a partir das coordenadas do Webnode (2 casas decimais ≈ 1 km: indicar que são aproximadas). Espaços sem coordenadas ficam fora do mapa. Nunca polígonos nesta fase.

## Constrangimentos conhecidos

- O hook do OneDrive impede-me de escrever ou executar sobre `Arquivo\`; por isso o trabalho parte da cópia em `docs/fonte_campanha/`.
- O PDF de 2016 tem 109 MB e mais de 146 páginas. A auditoria de imagens falhou por tempo (OCR); o texto das páginas amostradas existe, mas a cobertura total e a cor de fundo (que identifica a camada) só se confirmam nas imagens das páginas.
- Peso no repositório (PDFs de imprensa, fotos, anexos): medir antes de commitar.
- Regra de PDFs: antes de afirmar o que um PDF diz, correr `pdf_audit.py`.

## Pendente (a decidir ou verificar)

- Concelhos posteriores da AMP: fora desta fase (assumido).
- Tratamento da cor de fundo do PDF: extrair as camadas a partir das imagens das páginas ou só do texto.
- Reconciliar a lista final de 111 com as fichas dos 110 (zip) e 112 (projecto), incluindo extras (`arboreto escola EB2 Canelas`, `quinta dos ananases`, `espacos compilados`).
- Seleccionados: ver «Correcção de 2026-10-25» (feita na Tarefa 6).
- Comparar o Webnode com o PDF de 2016 em amostra (ex.: Parque Oriental).
- Ler as subpáginas `Apelo à CMP`, `Campanhã caso especial` e `Paradigma Dahlem` para decidir o que entra.
- Formulário de contribuições (Google Forms do Webnode): manter a ligação ou criar canal próprio.

## Escolhas minhas (a confirmar)

- Colecção `_espacos/` em vez de páginas soltas.
- Slug sem número de ficha.
- Estados do `estado_actual` listados acima.
- Concelhos novos da AMP fora do âmbito.
- Fotos redimensionadas na geração.

## Correcção de 2026-10-25 (Tarefa 6)

- **Não existe ordem de importância dos 50.** A coluna numérica da «Lista Final» (`2009-04-02 - SeleccaoEV.xlsx`) é um contador sequencial por concelho (1…48, monótono, sem cabeçalho). A decisão 6 («a ordem») e o campo `posicao_2009` ficam por isso sem fundamento e foram retirados; mostra-se só quem é dos 50.
- **Duas listas:** 48 espaços marcados `P` na lista final de 2009-04-02 e 50 na lista do livro (`Mais recente/50espacos - livro.xlsx`); os 2 a mais, Quinta da Bouça e Ribeira de Longras, entraram depois (`selecao: posterior`). O PDF de 2014–2016 também dá 50 seleccionados no índice (Porto 7, igual ao Webnode).
- **Datas:** o PDF «compilação» tem metadados de Setembro de 2018 e diz-se «versão de 2014-2016», não «2016».
- **Coordenadas do Webnode:** três longitudes sem sinal e uma gralha (Morro das Mimosas, −8,17); validação por caixa envolvente da AMP.
- **Camada «cidadãos» do PDF** contém nomes de contribuintes; decidir na fusão se se citam.
