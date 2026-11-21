# Horrores — galeria de casos do Porto (desenho)

*2026-11-21. Estado: **aprovado pelo utilizador** (2026-11-21), após leitura de construtor e revisão arquitectural (Opus). Nada construído; próximo passo: plano.*

## Intenção
Subprojecto do Porto Verde: mapa e galeria dos casos conhecidos, no concelho do Porto, de destruição ou perda urbanística, patrimonial e de verde que geraram contestação pública. Cada caso é um ponto com foto antes/depois, descrição curta e fontes. Mais tarde, a «galeria dos sucessos» (contraponto) com o mesmo modelo.
Disponível em dois sítios: tema novo do mapa único e páginas próprias.
**Porquê (por confirmar com o utilizador):** ainda não o disse com palavras suas; tom e rigor assumem documentação factual, não campanha.

## Decidido pelo utilizador
- Arquitectura **C**: uma só fonte por caso, duas saídas (tema do mapa único + página permanente por caso).
- Âmbito: **sem limite de data**, com arquivo; inclui abates de árvores/verde, demolições, edifícios classificados alterados, interiores destruídos, construções que descaracterizam.
- **Um só mapa**, filtro por tipo.
- Critério de entrada: **fonte documental de contestação** (notícia, petição, acta, queixa, parecer) **ou** lista de património em risco / classificação alterada. Só **se preciso**, juízo editorial do Porto Verde, marcado como tal.
- Fotos: as que se conseguirem, de terceiros com crédito; antes/depois não é obrigatório em par; na falta, Google (Street View/Earth) como último recurso.
- Janela: **hover = janela** (cartão compacto); **clique = ficha fixa**; fecha no ×; «mesmo modelo já usado».

## Objectivos / não-objectivos / anti-objectivos
- Objectivos: cobertura larga e verificável; cada caso com fonte citável; encaixe no mapa único e na moldura; reutilizável para «sucessos».
- Não-objectivos: ranking dos casos; polígonos/pegadas de edifícios (ponto basta); mapa ou fundo próprio; chat ou comentários.
- Anti-objectivos: virar opinião ou «naming and shaming»; factos sem fonte lida; página pesada; segundo mapa ou segundo escritor dos mesmos dados.

## Restrições do projecto (CLAUDE.md)
- HTML gerado nunca à mão; dados embutidos, nunca `fetch()` (`file://`); `Grep` dos consumidores ao mudar dados partilhados.
- «Nunca inventar referências»: nenhum autor/ano/título sem leitura na fonte; Haiku nunca cita (só verificação mecânica de existência).
- Sem dados pessoais (regra dos 50 Espaços, por analogia): nenhum nome de pessoa singular; instituições e empresas só se constarem da fonte.
- Fotos: nunca de utilizadores do Google Maps; crédito por foto.
- **Repositório público:** texto não revisto nunca entra nele (risco de difamação).
- Atribuição das fontes de dados na fonte do tema; `FONTES` em `moldura.js`; `test_moldura.py`.
- `_config.yml` `exclude` casa por prefixo: usar `"pasta/*"`; abrir o URL real antes de dar por publicado.
- Cálculos «só do concelho» (CAOP, `dtmn` 1312): casos fora do Porto não entram.
- **Não fundir com os 50 Espaços** (layout congelado a pedido do utilizador; campos e permalink da campanha). Reutilizar por importação, não por cópia (`slugify`).

## Abordagens consideradas
- **A. Só tema no mapa único:** sem link por caso. Rejeitada.
- **B. Sub-site autónomo (como 50 Espaços):** segundo mapa a manter. Rejeitada.
- **C. Fonte única, duas saídas (escolhida)**, refinada pela revisão arquitectural: sem gerador próprio. Cada caso é um ficheiro de colecção Jekyll editado e revisto (`_casos/<slug>.md`, como `_posts/`); o Jekyll gera páginas e índice; `mapa_unico.py` lê os mesmos ficheiros e escreve `dados/casos.js`. Retira o gerador, o formato `caso.yml`, o índice gerado e o campo `revisto`; um só escritor de cada saída.

## Desenho

### Ficheiros
```
_casos/<slug>.md                  # FONTE ÚNICA, só casos revistos (front matter = esquema; corpo = descrição)
Horrores/media/<slug>/            # fotos (JPEG ≤ 900 px, ~100 KB); pasta a confirmar pelo construtor
docs/horrores/rascunhos/<slug>.md # rascunhos NÃO revistos: gitignored; promover = mover para _casos/
docs/horrores.md                  # regras do subprojecto (curto; CLAUDE.md do projecto aponta para aqui)
Fontes\Horrores\<chave>\          # texto lido de cada fonte (armazém existente, fora do repositório)
mapa_unico/mapa_unico.py          # + dados_casos() → dados/casos.js
mapa_unico/src/tema_casos.js      # tema novo
casos/index.html                  # índice em Liquid (lista + filtro por tipo + ligação ao mapa)
tests (pytest): validador do esquema
```
URL das páginas: **`/casos/<slug>/`** (decidido pelo utilizador, 2026-11-21: espaço neutro, serve «horrores» e «sucessos»).

### Front matter do caso (esquema mínimo)
`titulo`, `galeria` (horrores|sucessos), `tipo` (arvores | demolicao | patrimonio_alterado | interiores_destruidos | descaracterizacao), `lat`, `lon`, `aproximada` (true se rua/ponto médio), `origem_coord`, `ano` (ou intervalo), `estado` (demolido | alterado | abatido | revertido | outro), `contestacao` (1 frase), `criterio` (documental | lista | editorial), `fotos: [{papel: antes|depois|outra, ficheiro, ano, fonte, url, sha256, nota}]`, `referencias: [{titulo, url, data, tipo, excerto}]`. Corpo = descrição de 3–5 linhas, voz neutra, juízo atribuído à fonte.
- `freguesia` **derivada** de lat/lon pela CAOP; ponto fora do 1312 = erro.
- `referencias` (não `fontes`): `default.html` põe `page.fontes` no rodapé e mostraria objectos em bruto.
- `excerto` = citação literal, verificada por máquina contra o texto guardado em `Fontes\Horrores\`, no estilo de `scripts/research_fetch.py verify` (mecanismo existente a confirmar no plano). Páginas com paywall/JS → leitura manual registada.
- Validador (pytest/pre-commit): esquema, ≥1 referência com excerto verificado, `lat/lon` dentro do concelho, fotos com `url` de origem, `criterio: editorial` mostra «avaliação do Porto Verde». Erros claros.
- `pyyaml` entra em `requirements.txt`.

### Mapa único
- Tema novo (`tema_casos.js`, hash `#tema=…`), pontos por tipo (paleta de dados, distinguíveis para daltónicos), filtro por tipo e por galeria (Horrores | Sucessos), `aproximada` desenhada com marca própria; cartão «Números» = contagens dos dados.
- **Hover:** janela compacta (foto, título, ano, tipo). **Clique:** ficha fixa, com ×, fecha ao clicar no mapa; antes|depois, descrição, estado, referências, «Ver página do caso →». Em ecrã táctil o clique abre a ficha (testar com `hasTouch`).
- Implementação: campo opcional `corpo` (HTML) em `MU.ficha` (`core.js`), sem `fichaCaso` paralelo; testes `pw_*` dos outros temas a correr antes e depois.
- Fotos por `<img src>` relativo injectadas só ao abrir a janela (peso não cresce com o nº de casos; `file://` ok).
- Página do caso liga ao mapa por `mapa_unico.html#tema=…&caso=<slug>` (`aoHash`), sem mini-mapa próprio.

### Pesquisa e produção
1. **F0 — Piloto (3 casos de tipos diferentes, de ponta a ponta):** esquema, validador, tema, página e janela validados antes de escalar. Casos propostos por mim, escolhidos pelo utilizador.
2. **F1 — Candidatos:** pesquisa online por fonte e por tipo (imprensa, petições, actas CMP/Assembleia Municipal, DGPC/património em risco, associações, arquivos: Arquivo Municipal do Porto, Wayback), agentes Sonnet com `model` explícito; texto lido guardado em `Fontes\Horrores\`; saída em `docs/horrores/rascunhos/`; **o utilizador escolhe** o que avança. Fontes concretas confirmadas com `WebSearch`, nunca de memória.
3. **F2 — Fichas e fotos em lote:** texto factual com `excerto` verificável; fotos por hierarquia (ortofotos públicas → arquivos → imprensa com crédito → Google como último recurso, com termos confirmados antes de guardar/republicar; se não permitirem, ligação externa em vez de ficheiro); revisão humana foto a foto; só então passa a `_casos/`.
4. **F3 — Sucessos:** `galeria: sucessos`; sem código novo.

## Chamadas minhas (para corrigir)
- 5 tipos (`interiores_destruidos` sem relação com o tema «Verde privado»); esquema acima; `aproximada` para casos sem ponto exacto.
- Voz documental; sem nomes de pessoas singulares.
- Rascunhos fora do repositório (gitignored); promover = mover.
- Ortofotos: a de 1947 vem do WMS CIIMAR/FCUP (já no projecto); outras datas (DGT/CMP) a confirmar na F1.
- Regras do subprojecto em `docs/`, não em `Horrores/CLAUDE.md` (o `exclude` casa por prefixo).

## Deixado ao construtor
Marcadores, layout da página do caso, pasta exacta das fotos, formato da janela de hover, recorte de ortofoto, `exclude` do `_config.yml`, `moldura.js` e `test_moldura.py`, testes Playwright.

## Riscos
- Difamação/exactidão: fonte lida com excerto verificável, voz neutra, rascunhos fora do repositório, sem pessoas.
- Direitos de imagem: crédito por foto; remover a pedido.
- Fotos de outro edifício não se validam por máquina: `url` de origem + `sha256` + revisão humana.
- Peso: fotos medidas em ~100 MB a juntar aos 163 MB de `50espacos/media` (estimativa).
- Cobertura nunca «completa»: dizê-lo na página («casos conhecidos e documentados»).
