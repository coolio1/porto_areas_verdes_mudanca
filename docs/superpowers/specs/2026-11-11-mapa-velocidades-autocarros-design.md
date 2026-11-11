# Mapa de velocidades dos autocarros — desenho

*2026-11-11. Rascunho para aprovação do utilizador.*

## Intenção

Um mapa para publicar no Porto Verde que mostre **as zonas específicas onde os autocarros andam muito devagar**. O leitor abre a página e vê logo, pela cor e pelo tamanho, os pontos críticos da rede de autocarros do Porto. A velocidade média é o dado; o objectivo é apontar sítios concretos (ruas, cruzamentos) que se possam citar em artigos e na discussão de faixas BUS.

## Dados (verificados em 2026-11-11)

- A VPS Hetzner recolhe desde 2026-11-08 as posições dos autocarros da **STCP** (script `Mobilidade/recolher_autocarros.py`, ver memória `reference_vps_recolha_autocarros`). Um CSV por dia (`recebido_utc, observado_utc, veiculo, lon, lat, velocidade, direccao, linha, sentido, viagem`). A `velocidade` está em **m/s** (confirmado pelo utilizador).
- Cada veículo dá **uma posição por minuto** (mediana 61 s), ou seja, uma a cada ~235 m. Nunca há cobertura contínua ao longo da rua.
- Cobertura: 4 dias (domingo 8 só à tarde, segunda 9 e terça 10 completas, quarta 11 até às 11h), ~400 autocarros e 71 linhas por dia, 552 mil leituras. Só STCP: **não é toda a AMP** (faltam os outros operadores).
- Qualidade: 142 leituras descartadas (atraso de recepção negativo ou > 300 s, ou velocidade > 90 km/h; houve um pico de 155 km/h). Sem coordenadas fora de zona.
- Perfil: velocidade média ~27 km/h de madrugada, ~12 km/h às 8h e às 17h–18h; só em andamento passa de ~35 a ~20 km/h. 35 % das leituras em dias úteis têm velocidade 0. No domingo à tarde a média é ~17–18 km/h (dias úteis à mesma hora: ~14).
- **Fim-de-semana:** só há o domingo à tarde. O primeiro fim-de-semana completo fica pronto a 2026-11-16.
- **Traçado das linhas:** o GTFS da STCP já não está no portal de dados abertos do Porto (404; o dataset está arquivado em dados.gov.pt). O OpenStreetMap tem 140 relações `route=bus` com `operator=STCP` (72 `ref` distintas), que cobrem **69 das 71 linhas dos dados (98,7 % das leituras)**; faltam a **107** e a **605**. Está também no OSM a rede UNIR/Andante (outros operadores), útil se os dados vierem a cobrir mais do que a STCP.
- **Paragens:** 6 972 paragens e estações do OSM (Overpass) como fonte provisória.

## Objectivos

1. Mostrar os pontos críticos como **localizações exactas**, sem quadrículas: troços de rua coloridos ao longo do traçado real das linhas, mais **marcadores com o nome da rua e do cruzamento** nos piores pontos.
2. **Críticos = lentos e muito usados.** O tamanho do destaque é o tempo de autocarro perdido por hora (passagens por hora × atraso face a 25 km/h). A cor é a velocidade média.
3. **Selector de período:** dia todo, ponta da manhã, ponta da tarde. **Dias úteis e fim-de-semana separados.**
4. **Actualização automática:** o mapa melhora à medida que a recolha avança; o gerador volta a correr sobre os dados mais recentes, sem editar HTML à mão.
5. Estilo **B**: fundo discreto, só os críticos em destaque, sobre o mapa-base **CARTO Positron** (claro), tal como o dashboard de atropelamentos.
6. Honestidade: título e aviso dizem que são **só autocarros STCP**, que há N dias de dados, e que as esperas em paragens foram descontadas.
7. A «Mobilidade» é a **secção-mãe** do site: os atropelamentos entrarão nela mais tarde, por isso a página, a pasta e o menu têm de o permitir.

## Não-objectivos

- Cobrir toda a AMP ou outros operadores (os dados só trazem STCP). O mapa não diz «AMP».
- Mover agora o dashboard de atropelamentos para a Mobilidade (fica para depois; o desenho só tem de o permitir).
- Previsões, comparações com horários (GTFS) ou atrasos face ao plano.
- Quadrículas, malhas hexagonais ou superfícies suavizadas.
- Mostrar leituras individuais ou identificar veículos.

## Anti-objectivos (falha mesmo que funcione)

- **Terminais e paragens aparecerem como pontos críticos** por esperas normais (a Campanhã tem 60–80 % de leituras a zero e não é congestionamento).
- **Descartar zeros devidos a trânsito** (o utilizador avisou). Só se descarta zero junto de paragem quando o trânsito à volta está fluido.
- Um troço aparecer **na rua errada** (ruas paralelas, túneis, cruzamentos).
- Apresentar como medido o que é amostra pequena (troços e períodos com poucas leituras ficam sem cor, não com um valor duvidoso).
- Dados pessoais, o IP da VPS ou a chave SSH no repositório (o repo é público).

## Decisões do utilizador

| Tema | Decisão |
|---|---|
| Mensagem do mapa | zonas onde os autocarros andam muito devagar |
| Período | selector dia todo / ponta da manhã / ponta da tarde |
| Dias | úteis e fim-de-semana separados; os dados melhoram sozinhos |
| Paragens e terminais | descontar as esperas, manter os zeros por trânsito |
| Representação | estilo B (fundo discreto, críticos em destaque), mapa-base OSM Positron |
| Definição de «crítico» | lento e muito usado; tamanho ∝ tempo perdido |
| Localização | ruas coloridas ao longo do traçado das linhas + marcadores com nome, sem quadrículas |
| Onde fica | página própria «Mobilidade», que mais tarde recebe os atropelamentos |

## Decisões minhas (marcadas, para confirmar ao ler)

- **Períodos (em hora local):** dia todo 6h–21h59, ponta da manhã 7h–9h59, ponta da tarde 17h–19h59. Valores da maquete.
- **Esperas:** uma leitura com velocidade ≤ 2 km/h a menos de 40 m de uma paragem é espera, salvo se ≥ 2 leituras de outros veículos fora de paragens, a < 300 m e ± 3 min tiverem mediana < 8 km/h (então é fila e mantém-se). Medido com o método final (564 835 leituras, 8–11 de Novembro, esperas + paradas longas): 18,2 % das leituras são espera e 15,6 % são zeros mantidos como trânsito. (Os valores da fase exploratória, 15 % e 9 281, foram substituídos.)
- **Tempo perdido** = passagens por hora × (tempo a atravessar o troço à velocidade medida − tempo a 25 km/h), com velocidade mínima de 2 km/h no cálculo.
- **Limiar visual:** só troços abaixo de 14 km/h têm destaque; o resto fica em cinzento discreto.
- **Amostra mínima:** a maquete exigia ≥ 20 leituras por zona de 250 m; para troços de rua o mínimo tem de ser fixado com os dados (pergunta ao construtor).
- **Colagem às linhas:** cada leitura é colada ao traçado da sua `linha`+`sentido`; o mapeamento de `sentido` para a relação OSM terá de ser verificado.
- **Linhas 107 e 605:** ficam de fora (1,3 % das leituras) e o aviso do mapa di-lo, a menos que se obtenha o traçado.
- **Página:** Leaflet com dados embutidos no HTML (regra do projecto: sem `fetch()`), chave CARTO via `aplicar_chave`, menu só em `nav.py`.

## Decisões minhas, depois da leitura do revisor (marcadas)

- **Esperas inconclusivas:** junto de uma paragem, com < 2 leituras de vizinhos para testar o trânsito, o zero conta como **espera** (descarta-se). É o lado seguro contra terminais nos pontos críticos; como «crítico» pesa as passagens por hora, ruas pouco servidas quase nunca ficam críticas de qualquer modo. O raio de 40 m e a fonte OSM das paragens podem ser afinados: antes de fixar, medir a sensibilidade com 25, 40 e 60 m e olhar para os terminais conhecidos.
- **Veículos parados muito tempo** (garagem, terminal fora do raio de 40 m): ≥ 15 leituras seguidas do mesmo veículo a < 15 m (≥ 15 min) contam como espera mesmo longe de paragens. Mais de 15 minutos no mesmo ponto não é trânsito.
- **Git:** a pasta `Mobilidade/` continua ignorada; abrem-se excepções só para o gerador, os testes, o requirements e a página (decisão do utilizador, 2026-11-11). Recolhedor, `deploy/` e dados brutos ficam só no disco.
- **Unidade de agregação:** **troço físico de rua**, juntando todas as linhas que o usam (a chave é a geometria/via OSM), não linha a linha. Só assim há amostra suficiente. As passagens por hora somam todas as linhas; o popup lista as linhas que passam.
- **Tempo perdido:** calculado por troço, em minutos de autocarro por hora. **Marcadores:** troços críticos contíguos da mesma rua ou cruzamento fundem-se num ponto; no máximo ~15 por período e tipo de dia; o corte exacto fixa-se com os dados. Nome = rua principal + cruzamento mais próximo (OSM).
- **Orçamento da página:** alvo ≤ 3 MB de HTML. A geometria dos troços entra uma só vez e é simplificada; cada uma das 6 variantes (3 períodos × dia útil/fim-de-semana) leva só números por troço. Só troços com amostra suficiente entram.
- **Limiar de 14 km/h:** absoluto e fixo (não relativo), para o mapa não mudar de critério à medida que os dados crescem. A cor usa a **média das leituras**: como são tiradas a intervalos de tempo iguais, a média num troço dá distância/tempo do percurso. A confirmar contra a velocidade calculada pelos deslocamentos (a correlação medida foi 0,6, as medianas 14,2 e 14,9 km/h).
- **Fim-de-semana:** o botão fica visível e desactivado até haver sábado e domingo completos («a partir de 16 de Novembro»); depois activa-se. Cada período mostra «sem dados suficientes» onde não houver amostra. O aviso «N dias de dados» é por tipo de dia.
- **Amostra mínima por troço, período e tipo de dia:** ≥ 20 leituras, ≥ 3 veículos distintos e ≥ 2 dias distintos (para que um só autocarro lento não decida). Afinar com os dados.
- **Dados brutos:** `C:\Users\quent\Dados\autocarros\` (fora do OneDrive). A descarga da VPS é um passo separado (`scp`); o gerador lê dessa pasta.
- **Páginas e URL:** a pasta `Mobilidade/` já existe no repo (tem o recolhedor). A página nova fica lá dentro (por exemplo `Mobilidade/autocarros.html`) e a entrada do menu chama-se «Mobilidade». Quando os atropelamentos entrarem, o URL antigo passa a redirecionar pelo mecanismo de stubs existente. Cuidado com a diferença de maiúsculas entre Windows e GitHub Pages: usar sempre a grafia que está no git.

## Restrições do projecto

- Cada script gera o seu HTML; nunca editar HTML à mão. Dados inline. `aplicar_chave(html)` antes de gravar.
- O repositório do Porto Verde é público: nenhum dado bruto da recolha, nenhum IP, nenhuma chave.
- Os CSV brutos ficam fora do OneDrive (`scp` da VPS para uma pasta fora do sync); o gerador lê-os de lá.
- Ficheiros Python do `Mobilidade/` já existentes (`recolher_autocarros.py`, `verificar_recolha.py`) não se alteram sem necessidade.
- Pytest/`py_compile` antes e depois; nenhum cache de dependências no OneDrive.
- O **push** do repo do Porto Verde está fora do hook `guard-git-push.py` (repo público): quem publica é o utilizador.

## O que fica para o construtor

- Algoritmo de colagem às linhas (por exemplo, projecção da posição no traçado com restrição de sentido e direcção) e validação com pontos conhecidos.
- Segmentação das linhas em troços e o seu comprimento (a cobertura é de ~235 m por leitura).
- Nome da rua e do cruzamento para cada marcador (OSM).
- Forma de agregar passagens por hora e de combinar vários dias com o mesmo peso.
- Estrutura de pastas e do menu para a Mobilidade receber os atropelamentos.
- Como regenerar periodicamente (descarregar da VPS → gerar → o utilizador faz push).
- Testes do gerador (descarte de dados maus, regra das esperas, colagem às linhas).
