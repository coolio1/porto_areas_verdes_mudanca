import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.ts";

const ORIGEM = "https://portoverde.pt";
let turnstileOk = true;
let chamadasModelo = 0;
let logs: unknown[][] = [];

beforeEach(() => {
  turnstileOk = true;
  chamadasModelo = 0;
  logs = [];
  globalThis.fetch = (async () => new Response(JSON.stringify({ success: turnstileOk }))) as typeof fetch;
  for (const k of ["log", "info", "warn", "error"] as const) (console as any)[k] = (...a: unknown[]) => logs.push(a);
});

function kv() {
  const m = new Map<string, string>();
  return { m, get: async (k: string) => m.get(k) ?? null, put: async (k: string, v: string) => void m.set(k, v) };
}
function sse(...partes: string[]) {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(c) {
      for (const p of partes) c.enqueue(enc.encode(p));
      c.close();
    },
  });
}
function mkEnv(over: Record<string, unknown> = {}, chunks?: unknown[], resposta?: ReadableStream) {
  const cs = chunks ?? [
    { id: "1", score: 0.8, text: "Lisboa tem X casas vagas [p. 3].", item: { key: "ref218.md" } },
    { id: "2", score: 0.7, text: "Outro texto.", item: { key: "nota_04_a.md" } },
  ];
  return {
    LIMITES: kv(),
    TURNSTILE_SECRET: "s",
    SALT: "sal",
    ORIGEM_PERMITIDA: ORIGEM,
    AI_SEARCH: { get: () => ({ search: async () => ({ chunks: cs }) }) },
    AI: {
      run: async () => {
        chamadasModelo++;
        return resposta ?? sse('data: {"response":"Há casas vagas [1]"}\n\n', 'data: {"response":" e mais [99]."}\n\n', "data: [DONE]\n\n");
      },
    },
    ...over,
  } as any;
}
function pedido(corpo: unknown, ip = "1.2.3.4") {
  return new Request("https://api.exemplo/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json", origin: ORIGEM, "cf-connecting-ip": ip },
    body: JSON.stringify(corpo),
  });
}
const ok = { pergunta: "Quantas casas vagas há?", token: "t" };

test("pergunta vazia -> 400 vazia", async () => {
  const r = await worker.fetch(pedido({ ...ok, pergunta: "   " }), mkEnv());
  assert.equal(r.status, 400);
  assert.equal((await r.json()).erro, "vazia");
});

test("501 caracteres -> 400 longa", async () => {
  const r = await worker.fetch(pedido({ ...ok, pergunta: "a".repeat(501) }), mkEnv());
  assert.equal(r.status, 400);
  assert.equal((await r.json()).erro, "longa");
});

test("Turnstile falha -> 400 turnstile", async () => {
  turnstileOk = false;
  const r = await worker.fetch(pedido(ok), mkEnv());
  assert.equal(r.status, 400);
  assert.equal((await r.json()).erro, "turnstile");
});

test("11.ª pergunta do mesmo IP -> 429 limite_dia", async () => {
  const env = mkEnv();
  for (let i = 0; i < 10; i++) assert.equal((await worker.fetch(pedido(ok), env)).status, 200);
  const r = await worker.fetch(pedido(ok), env);
  assert.equal(r.status, 429);
  assert.equal((await r.json()).erro, "limite_dia");
  // outro IP continua a poder
  assert.equal((await worker.fetch(pedido(ok, "9.9.9.9"), env)).status, 200);
});

test("tecto mensal -> 503 tecto_mes", async () => {
  const env = mkEnv();
  const mes = new Date().toISOString().slice(0, 7);
  env.LIMITES.m.set(`m:${mes}`, "950");
  const r = await worker.fetch(pedido(ok), env);
  assert.equal(r.status, 503);
  assert.equal((await r.json()).erro, "tecto_mes");
});

test("sem chunks acima do limiar -> sem_fontes e o modelo nao e chamado", async () => {
  const env = mkEnv({}, []);
  const r = await worker.fetch(pedido(ok), env);
  assert.equal((await r.json()).erro, "sem_fontes");
  assert.equal(chamadasModelo, 0);
});

test("erro do AI Search -> 503 indisponivel", async () => {
  const env = mkEnv({ AI_SEARCH: { get: () => ({ search: async () => { throw new Error("x"); } }) } });
  const r = await worker.fetch(pedido(ok), env);
  assert.equal(r.status, 503);
  assert.equal((await r.json()).erro, "indisponivel");
});

test("erro do modelo (neuronios esgotados) -> 503 indisponivel", async () => {
  const env = mkEnv({ AI: { run: async () => { throw new Error("daily free allocation"); } } });
  const r = await worker.fetch(pedido(ok), env);
  assert.equal(r.status, 503);
  assert.equal((await r.json()).erro, "indisponivel");
});

test("sucesso: fontes antes dos deltas, citacao [99] removida, [1] mantida", async () => {
  const r = await worker.fetch(pedido(ok), mkEnv());
  assert.equal(r.status, 200);
  assert.match(r.headers.get("content-type")!, /text\/event-stream/);
  assert.equal(r.headers.get("access-control-allow-origin"), ORIGEM);
  const t = await r.text();
  assert.ok(t.indexOf("event: fontes") < t.indexOf('"t"'));
  assert.match(t, /Portaria/);
  const texto = [...t.matchAll(/data: \{"t":(".*?")\}/g)].map((m) => JSON.parse(m[1])).join("");
  assert.equal(texto, "Há casas vagas [1] e mais.");
  assert.match(t, /data: \[FIM\]/);
});

test("formato de delta OpenAI (choices[0].delta.content) tambem funciona", async () => {
  const resp = sse('data: {"choices":[{"delta":{"content":"Olá [2]"}}]}\n\n', "data: [DONE]\n\n");
  const t = await (await worker.fetch(pedido(ok), mkEnv({}, undefined, resp))).text();
  assert.match(t, /Olá \[2\]/);
});

test("a pergunta nunca vai para console", async () => {
  await worker.fetch(pedido({ ...ok, pergunta: "pergunta-secreta-123" }), mkEnv());
  assert.doesNotMatch(JSON.stringify(logs), /pergunta-secreta-123/);
});

test("origem nao permitida -> 403; OPTIONS responde CORS", async () => {
  const mau = new Request("https://api.exemplo/api/chat", { method: "POST", headers: { origin: "https://mau.pt" }, body: "{}" });
  assert.equal((await worker.fetch(mau, mkEnv())).status, 403);
  const op = await worker.fetch(new Request("https://api.exemplo/api/chat", { method: "OPTIONS", headers: { origin: ORIGEM } }), mkEnv());
  assert.equal(op.status, 204);
  assert.equal(op.headers.get("access-control-allow-origin"), ORIGEM);
});
