# Worker do chat (portoverde-chat)
Testes: `node --test test/nucleo.test.ts test/handler.test.ts` (Node 24, sem dependências; sem node_modules por estar no OneDrive).
Deploy: `npx wrangler deploy` (requer `npx wrangler login`); o contador é um Durable Object SQLite (migração `v1` no `wrangler.jsonc`, sem KV); segredos `TURNSTILE_SECRET` e `SALT`.
`../refs.json` é gerado por `AI Habitacao/scripts/gerar_refs_publico.py` (só citações públicas; nunca o corpus).
