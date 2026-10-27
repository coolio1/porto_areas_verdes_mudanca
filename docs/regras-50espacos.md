## 50 Espaços (`/50espacos/`)

Secção da campanha da Campo Aberto (111 espaços, 50 seleccionados). Spec e plano: `docs/superpowers/{specs,plans}/2026-10-25-50espacos-*.md`.

- **Pipeline** em `espacos_pipeline/` (pytest): extractores → `docs/fonte_campanha/extraido/*.json` (gitignored) → `reconciliar.py` (regra: prevalece o valor que 2+ fontes concordam; decisões em `docs/fonte_campanha/reconciliacao.md`) → texto fundido em `docs/50espacos/fusao/<concelho>/<slug>.md` → `gerar.py` escreve `_espacos/**` e `_data/espacos_mapa.json`. Nunca editar `_espacos/**` à mão.
- **Fontes fora de Claude (2026-10-27):** os repositórios de entrada (fichas do site, pasta do projecto, PDF de 2016) vivem em `OneDrive\Arquivo\Campo Aberto` (`Projectos\50 Espacos Verdes`, `Internet\50 Espacos Verdes`, `Internet\www.campoaberto.pt\...\111espacos-TOTAL.pdf`) e o pipeline lê-os por `espacos_pipeline/fontes.py` (único sítio a mudar se o utilizador renomear pastas do Arquivo, como fez a 2026-10-27). Em `docs/fonte_campanha/` ficam só as saídas (`extraido/`, `webnode/`, `reconciliacao.md`); `projecto/`, `site_zip/` e `pdf2016/` são cópias antigas (cerca de 3 GB), dispensáveis. Nenhum PDF de `fonte_campanha` existia só em Claude (146 de 146 tinham cópia no Arquivo).
- **Só se publica texto com `revisto: true`** no front matter; o utilizador revê antes.
- **Sem dados pessoais**: nada de nomes de pessoas singulares (proponentes, contributos) nem contactos; instituições sim. `docs/50espacos/dossiers/` é gitignored (tem nomes das fontes).
- **Não existe ranking** dos 50; `selecao` = `2009-04` ou `posterior`. Coordenadas aproximadas (2 casas decimais), sempre com `origem_coord`.
- Fotos/PDFs de apoio em `50espacos/media/<slug>/`, imprensa em `50espacos/imprensa/` + `_data/imprensa.yml`. Contributos: email `contacto@campoaberto.pt` (sem formulário).
- Fase 1 = Porto (23). Os outros concelhos reutilizam o mesmo pipeline.
