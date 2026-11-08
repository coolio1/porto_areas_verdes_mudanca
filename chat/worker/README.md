# Worker do chat (portoverde-chat)
Testes: `node --test test/nucleo.test.ts test/handler.test.ts` (Node 24, sem dependências; sem node_modules por estar no OneDrive).
Deploy: `npx wrangler deploy` (requer `npx wrangler login`); criar o KV (`npx wrangler kv namespace create LIMITES`) e pôr o id no `wrangler.jsonc`; segredos `TURNSTILE_SECRET` e `SALT`.
`../refs.json` é gerado por `AI Habitacao/scripts/gerar_refs_publico.py` (só citações públicas; nunca o corpus).
