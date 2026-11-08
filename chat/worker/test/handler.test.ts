import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.ts";
import { contar } from "../src/contador.ts";
import { consumir } from "../src/limites.ts";

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

function fakeContador() {
  const m = new Map<string, unknown>();
  const kv = {
    get: (k: string) => m.get(k),
    put: (k: string, v: unknown) => void m.set(k, v),
    delete: (k: string) => void m.delete(k),
    list: (o: { prefix: string }) => [...m].filter(([k]) => k.startsWith(o.prefix)),
  };
  return {
    storage: m,
    idFromName: (n: string) => n,
    get: () => ({
      fetch: async (_u: string, init: { body: string }) => {
        const { h } = JSON.parse(init.body);
        return new Response(JSON.stringify({ r: contar(kv, h, new Date().toISOString()) }));
      },
    }),
  };
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
    CONTADOR: fakeContador(),
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
  env.CONTADOR.storage.set(`m:${mes}`, 950);
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

test("erro generico do modelo -> 503 indisponivel", async () => {
  const env = mkEnv({ AI: { run: async () => { throw new Error("timeout do modelo"); } } });
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

test("contador atomico: 20 pedidos em paralelo com 9 usados deixam passar exactamente 1", async () => {
  const env = mkEnv();
  for (let i = 0; i < 9; i++) assert.equal(await consumir(env, "7.7.7.7"), "ok");
  const r = await Promise.all(Array.from({ length: 20 }, () => consumir(env, "7.7.7.7")));
  assert.equal(r.filter((x) => x === "ok").length, 1);
});

test("IPv6: enderecos do mesmo /64 partilham o limite", async () => {
  const env = mkEnv();
  for (let i = 0; i < 10; i++) assert.equal(await consumir(env, `2001:db8:1:2:${i}::1`), "ok");
  assert.equal(await consumir(env, "2001:db8:1:2:ffff::9"), "limite_dia");
  assert.equal(await consumir(env, "2001:db8:1:3::1"), "ok");
});

test("sem SALT -> 503 indisponivel (nunca hash reversivel)", async () => {
  const r = await worker.fetch(pedido(ok), mkEnv({ SALT: undefined }));
  assert.equal(r.status, 503);
  assert.equal((await r.json()).erro, "indisponivel");
});

test("contador a falhar -> 503 indisponivel com CORS", async () => {
  const env = mkEnv({ CONTADOR: { idFromName: () => "x", get: () => ({ fetch: async () => { throw new Error("DO em baixo"); } }) } });
  const r = await worker.fetch(pedido(ok), env);
  assert.equal(r.status, 503);
  assert.equal((await r.json()).erro, "indisponivel");
  assert.equal(r.headers.get("access-control-allow-origin"), ORIGEM);
});

test("corpo JSON null -> 400 vazia", async () => {
  const r = await worker.fetch(pedido(null), mkEnv());
  assert.equal(r.status, 400);
  assert.equal((await r.json()).erro, "vazia");
});

test("ultima linha do stream sem \n final nao se perde", async () => {
  const resp = sse('data: {"response":"A [1]"}\n\n', 'data: {"response":" B"}');
  const t = await (await worker.fetch(pedido(ok), mkEnv({}, undefined, resp))).text();
  const texto = [...t.matchAll(/data: \{"t":(".*?")\}/g)].map((m) => JSON.parse(m[1])).join("");
  assert.equal(texto, "A [1] B");
});

test("cancelar a resposta cancela o stream do modelo", async () => {
  let cancelado = false;
  const origem = new ReadableStream({ pull() {}, cancel() { cancelado = true; } });
  const r = await worker.fetch(pedido(ok), mkEnv({}, undefined, origem));
  const leitor = r.body!.getReader();
  await leitor.read(); // evento fontes
  await leitor.cancel();
  await new Promise((x) => setTimeout(x, 10));
  assert.equal(cancelado, true);
});

test("Turnstile inacessivel (rede) -> 503 indisponivel, nao 'turnstile'", async () => {
  globalThis.fetch = (async () => { throw new Error("rede"); }) as typeof fetch;
  const r = await worker.fetch(pedido(ok), mkEnv());
  assert.equal(r.status, 503);
  assert.equal((await r.json()).erro, "indisponivel");
});

test("neuronios esgotados -> 503 limite_servico (distinto de indisponivel)", async () => {
  const env = mkEnv({ AI: { run: async () => { throw new Error("You have used up your daily free allocation of 10,000 neurons"); } } });
  const r = await worker.fetch(pedido(ok), env);
  assert.equal(r.status, 503);
  assert.equal((await r.json()).erro, "limite_servico");
});

test("chunk sem item nao rebenta (503, nao 500)", async () => {
  const env = mkEnv({}, [{ id: "1", score: 0.9, text: "x" }]);
  const r = await worker.fetch(pedido(ok), env);
  assert.ok(r.status === 200 || r.status === 503);
});
