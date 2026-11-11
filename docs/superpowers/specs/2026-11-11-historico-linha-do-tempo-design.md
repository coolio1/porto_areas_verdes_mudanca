# Histórico do uso do solo: linha do tempo, comparação e números

*Desenho de 2026-11-11. Projecto: Porto Verde. Âmbito: o tema «Histórico 1947-2024» da página `mapa_unico/` (`mapa_unico/src/tema_historico.js` e o gerador `mapa_unico/mapa_unico.py`).*

## Intenção e porquê

O utilizador acha o separador Histórico **confuso** e pediu: retirar o NDVI e pensar como melhorá-lo «substancialmente», com as épocas **do mais recente para o mais antigo**. Hoje o painel tem cerca de 30 caixas em 7 grupos (1947, 1979, vegetação por época, edificado por época, perda e ganho, NDVI, contexto), abre com a vegetação de 1947 a cobrir quase a cidade toda e não conta uma história. Quem chega não sabe o que ver nem o que comparar.

O que o separador tem para dizer é **como o Porto perdeu verde e ganhou construído desde 1947**. O desenho serve esse objectivo: ver uma época de cada vez, comparar duas épocas lado a lado e ler os números de relance.

## Objectivos

1. **Retirar o NDVI** do `mapa_unico` (grupo, camadas e dados embutidos). A página separada `ndvi_historico/` e os PNG em `layers_historico/` não se tocam.
2. **Linha do tempo** em vez das caixas: botões em fila, **do mais recente ao mais antigo** — 2023-24, 2016-17, 2001-05, 1995-2000, 1985-90, 1979, 1972-76, 1947. Escolher uma mostra, nesse mapa, a vegetação e o edificado dessa época (um só par de cada vez). Abre em 2023-24.
3. **Comparar:** botão «Comparar» que abre uma **cortina deslizante** (esquerda uma época, direita outra), com selectores das duas épocas; por omissão 2023-24 contra 1947. Qualquer par de épocas serve (cada época é uma camada própria; não depende de diferenças pré-calculadas).
4. **Números:** minigráfico clicável com a percentagem de vegetação e de edificado do concelho do Porto em cada época; clicar numa época salta para ela. Valores calculados pelo gerador a partir dos próprios mapas (pixels/áreas) e gravados nos dados.
5. **Fonte e resolução de cada época** numa linha visível (ortofoto 1947; Landsat MSS 60 m em 1972-76; Landsat 30 m de 1985 em diante; ocupação do solo vectorial de Filipa Guilherme em 1979).
6. **1979:** na linha do tempo e na cortina mostra vegetação e edificado como as outras épocas (vegetação = árvores, arbustos e herbáceas; edificado = elementos artificiais, como já está nas máscaras `veg_1979`/`edif_1979`). Um botão «ver as 5 classes» abre o detalhe original de Filipa Guilherme (polígonos com popups).
7. **Perda e ganho** (85-90 → 23-24) continua disponível como uma vista simples (um interruptor), não como grupo de caixas.
8. **Contexto** (limites municipais, densidade, fundos de mapa, incluindo a ortofoto 1947 como fundo) mantém-se, mas recolhido.

## Não-objectivos

- Não se mexe nos dados nem nos pipelines que produzem as máscaras (NDVI ≥ 0,25, Roy et al. 2016; classificação de 1947 com Random Forest e limpeza com `clean_1947.py`).
- Não se calculam novas diferenças entre épocas; a cortina compara visualmente.
- Não se mexe nos outros três temas do `mapa_unico` nem em `ndvi_historico/`.
- Não se acrescentam épocas nem fontes novas.

## Anti-objectivos (falha mesmo que «funcione»)

- Ler a evolução como **série contínua rigorosa**: as épocas vêm de sensores e resoluções diferentes (1947 ortofoto, 1972-76 a 60 m, restantes a 30 m) e a definição de «vegetação» difere (RF em 1947, NDVI ≥ 0,25 nos Landsat, classes de ocupação do solo em 1979). Parte das diferenças pode ser artefacto. O painel tem de dizer a fonte e a resolução de cada época e **não pode afirmar tendências** que os dados não sustentam; 1947 e 1972-76 levam ressalva escrita.
- Números no painel que **não confiram com os mapas** (cada percentagem tem de poder verificar-se por contagem de pixels/áreas no mesmo concelho).
- Perder o que existe hoje: o popup e os totais em hectares de 1979, a opacidade da camada de 1947, a opção da ortofoto 1947 como fundo, e o parâmetro de URL `#tema=historico` (e `vista=1947`).
- Página pesada: hoje `dados/historico.js` tem 7,1 MB; retirar o NDVI deve **reduzi-lo**, nunca aumentá-lo.

## Restrições

- Texto em PT-PT pré-acordo; épocas e listas do mais recente para o mais antigo; sem quebra de palavras em fim de linha.
- Dados embutidos em `mapa_unico/dados/*.js`, nunca `fetch()` (os mapas abrem-se em `file://`). O HTML e os dados são gerados por `mapa_unico/mapa_unico.py` (nunca à mão); `--html` regenera só o HTML, o resto demora ~2 min por causa das máscaras de 1947.
- Funciona no telemóvel: a linha do tempo e a cortina têm de caber e usar-se com o dedo.
- Cores das épocas já gravadas nas máscaras (vegetação `#00FF00`, edificado `#C4A882`); a 1947 é tingida por filtro SVG (sem canvas de 170 Mpx). Manter estas técnicas.
- 1947 tem outra grelha (`BOUNDS_1947`) e resolução; a cortina tem de funcionar com ela e com as grelhas Landsat (`MU.BOUNDS`).
- Verificação em `file://` com Playwright (Edge `channel="msedge"`); o hook bloqueia `sed -i` no OneDrive (usar Edit).

## Decisões do utilizador

- Ordem das épocas: **do mais recente para o mais antigo** (pedido dele).
- Controlo: **linha do tempo + cortina de comparação** (escolhida entre três).
- 1979: **2 classes na linha do tempo + detalhe das 5 classes opcional**.
- Números: **minigráfico clicável** com a percentagem por época.
- «Pensa tu»: o resto do desenho (cortina, contexto recolhido, perda e ganho como interruptor) é escolha minha, a rever por ele.

## Decisões minhas (a rever pelo utilizador; resultado da revisão do construtor)

1. **Percentagens:** denominador = área do concelho (`porto_mask.png`) para todas as épocas, para serem comparáveis. Vegetação e edificado não precisam de somar 100 %: o resto (solo nu, água, 1979 «esparsa» e «aquática») fica de fora e diz-se no painel. Se uma época não cobrir todo o concelho (1947 tem grelha própria), a barra leva a % de cobertura numa nota; nunca se omite em silêncio. Se a cobertura de uma época for inferior a 95 %, o construtor pára e pergunta.
2. **Perda e ganho:** interruptor que **substitui** o par vegetação/edificado da época escolhida pela diferença 85-90 → 23-24; escolher uma época desliga-o; na cortina não está disponível (só pares de épocas).
3. **Opacidade e cores:** um único controlo de opacidade global das camadas de época (inclui a 1947, que já o tinha); a edição de cores por camada sai (as cores são as das máscaras e a legenda é fixa). Sem selectores de cor, a legenda fica mais clara.
4. **Minigráfico:** barras separadas por época, nunca uma linha contínua; 1947, 1972-76 e 1979 marcadas com símbolo de «fonte diferente» e ressalva na legenda.
5. **URLs:** `#tema=historico` abre em 2023-24; `vista=1947` selecciona a época 1947 e liga a ortofoto como fundo (as ligações antigas continuam a funcionar).

## O que fica ao construtor

- Mecanismo da cortina (por exemplo recorte de `pane` com um separador arrastável) e o estilo dos botões, do minigráfico e da linha de fonte, no estilo existente do `mapa_unico` (`MU.*`).
- Como calcular as percentagens (contagem de pixels não transparentes das máscaras dentro de `porto_mask.png`; 1947 pelas suas camadas; 1979 pelas áreas vectoriais) e onde gravá-las nos dados.
- Redacção das linhas de fonte e das ressalvas (sem inventar referências: usar só as que o `fonte:` do tema já cita).
- Verificar se as máscaras 1972-76 e 1947 cobrem o mesmo concelho antes de calcular percentagens comparáveis.

## Riscos que o desenho não elimina

- Comparabilidade entre épocas (ver anti-objectivos): mitigada com avisos, não eliminada.
- A cortina entre grelhas de resolução diferente (1947 contra Landsat) pode mostrar «blocos» de 30/60 m ao lado de detalhe fino; é uma limitação do dado.
- Percentagens dependem da definição de classe de cada época; o gráfico mostra-as, mas não as torna comparáveis em rigor.
