# Template «Atlas» — notas em PDF do Porto Verde

Desenho da nota da habitação (v27, 2026-11-15) tornado genérico: capa escura, índice, aberturas de secção com cor própria, camada «Ler primeiro», texto a duas colunas, abas laterais e rodapé com trilho. Fonte de verdade do desenho: `nota.css` (cópia de `../pdf-habitacao/nota.css`; mudar o desenho aqui não muda a nota da habitação).

## Usar numa nota nova
1. Copiar esta pasta para `_build/<nota>/`; editar `nota.json` e escrever o `.md` (substitui `exemplo.md`).
2. Construir: `PDF_OUT=<scratchpad>/<nota> python build.py --md <nota>.md --cfg nota.json` (com `uv run --no-project --with-requirements requirements.txt`). Escrever PDF directamente no OneDrive pode falhar: `PDF_OUT` na scratchpad e `cp` para `assets/pdfs/`. `PW_CHROME` = Chromium instalado, se o do playwright não casar.
3. Ver as páginas (imagem), não só o texto; depois publicar com `! python ~/.claude/scripts/publicar.py porto-verde --permitir <nome>.pdf` (corre o utilizador).

## Convenções do markdown
- `## N Título` = secção (abertura escura, cor `cores[N-1]`); `### N.M Título` = subsecção (entra em «Nesta secção» e no índice); `## Referências` sem número = cinzento. Linha em branco antes de `## Referências`.
- Figura: `<div class="graf"><img src="caminho/absoluto.png"><p class="leg"><span class="fl">Figura 1</span> Legenda.</p></div>`.
- Frase em destaque: `::: destaque` … `:::`.
- Tabelas em pipe; identificadores com hífen que não devem partir: `<span class="nq">…</span>` (o resto parte-se sozinho).
- Camada de leitura: `nota.json → ler["<N>"] = {resumo, numeros[3]}`. **Só texto e números que existem na secção** (nada novo); a linha de aviso na página diz isso. Sem entrada, a abertura sai só com a lista.

## `nota.json`
`marca`, `etiqueta` (rodapé), `cabecalho`, `kicker`, `titulo`, `subtitulo`, `imagem` (caminho relativo a esta pasta ou `null`), `legenda_imagem`, `numeros` (2 pares valor/rótulo na capa), `aviso`, `cores` (5 hex sem `#`), `saida`.

## Lições (da nota da habitação)
- Chromium escreve `text-transform:uppercase` em maiúsculas: pesquisas de texto no PDF, sem distinguir caixa.
- A abertura tem de ser irmã da sua secção no HTML (feito em `nohyphen`), senão a paginação desfaz-se (52 páginas em vez de 113).
- Detecção de aberturas por pixel (fundo escuro), não por texto: um texto que cite «secção» confundia-se com abertura.
- NBSP só em texto, nunca dentro de tags (parte `viewBox` e pontos de SVG).
- Após o build: conferir que nenhuma linha acaba em hífen (só URLs) e que a lista de aberturas cabe (secções com > 9 subsecções passam a duas colunas).
