import { consumir } from "./limites.ts";
import { verificarTurnstile } from "./turnstile.ts";
import { montarMensagens, type Chunk } from "./prompt.ts";
import { keyParaFonte } from "./fontes.ts";
import { deltaDe, ValidadorFluxo } from "./stream.ts";

const MODELO = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const MAX_PERGUNTA = 500;
const LIMIAR = 0.4;

type Env = any; // sem @cloudflare/workers-types (node_modules fora do OneDrive)

function cors(env: Env): Record<string, string> {
  return { "access-control-allow-origin": env.ORIGEM_PERMITIDA, "access-control-allow-methods": "POST, OPTIONS", "access-control-allow-headers": "content-type", vary: "origin" };
}
function erro(env: Env, codigo: string, status: number): Response {
  return new Response(JSON.stringify({ erro: codigo }), { status, headers: { "content-type": "application/json", ...cors(env) } });
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    if (req.headers.get("origin") !== env.ORIGEM_PERMITIDA) return new Response("origem não permitida", { status: 403 });
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(env) });
    if (req.method !== "POST") return erro(env, "metodo", 405);

    let corpo: { pergunta?: unknown; token?: unknown };
    try {
      corpo = await req.json();
    } catch {
      return erro(env, "vazia", 400);
    }
    const pergunta = typeof corpo.pergunta === "string" ? corpo.pergunta.trim() : "";
    if (!pergunta) return erro(env, "vazia", 400);
    if (pergunta.length > MAX_PERGUNTA) return erro(env, "longa", 400);

    const ip = req.headers.get("cf-connecting-ip") ?? "0.0.0.0";
    if (!(await verificarTurnstile(String(corpo.token ?? ""), ip, env.TURNSTILE_SECRET))) return erro(env, "turnstile", 400);

    const c = await consumir(env, ip);
    if (c !== "ok") return erro(env, c, c === "limite_dia" ? 429 : 503);

    let chunks: Chunk[];
    try {
      const r = await env.AI_SEARCH.get("nota-habitacao").search({
        query: pergunta,
        ai_search_options: { retrieval: { max_num_results: 6, match_threshold: LIMIAR } },
      });
      chunks = (r.chunks ?? []).filter((x: Chunk) => x.score >= LIMIAR);
    } catch {
      return erro(env, "indisponivel", 503);
    }
    if (chunks.length === 0) {
      return new Response(JSON.stringify({ erro: "sem_fontes" }), { status: 200, headers: { "content-type": "application/json", ...cors(env) } });
    }

    let origem: ReadableStream;
    try {
      origem = await env.AI.run(MODELO, { messages: montarMensagens(pergunta, chunks), stream: true, max_tokens: 700 });
    } catch {
      return erro(env, "indisponivel", 503);
    }

    const fontes = chunks.map((ch, i) => {
      const f = keyParaFonte(ch.item.key);
      return { n: i + 1, titulo: f?.titulo ?? ch.item.key, url: f?.url ?? null };
    });
    const validos = new Set(fontes.map((f) => f.n));
    const val = new ValidadorFluxo(validos);
    const enc = new TextEncoder();
    const dec = new TextDecoder();
    const emitir = (t: string) => (t ? enc.encode(`data: ${JSON.stringify({ t })}\n\n`) : null);

    const saida = new ReadableStream({
      async start(ctrl) {
        ctrl.enqueue(enc.encode(`event: fontes\ndata: ${JSON.stringify(fontes)}\n\n`));
        const leitor = origem.getReader();
        let resto = "";
        try {
          for (;;) {
            const { done, value } = await leitor.read();
            if (done) break;
            resto += dec.decode(value, { stream: true });
            const linhas = resto.split("\n");
            resto = linhas.pop() ?? "";
            for (const l of linhas) {
              if (!l.startsWith("data:")) continue;
              const d = l.slice(5).trim();
              if (d === "[DONE]") continue;
              const e = emitir(val.push(deltaDe(d)));
              if (e) ctrl.enqueue(e);
            }
          }
          const e = emitir(val.fim());
          if (e) ctrl.enqueue(e);
          ctrl.enqueue(enc.encode("data: [FIM]\n\n"));
        } catch {
          ctrl.enqueue(enc.encode(`event: erro\ndata: {"erro":"indisponivel"}\n\n`));
        }
        ctrl.close();
      },
    });
    return new Response(saida, { headers: { "content-type": "text/event-stream", "cache-control": "no-cache", ...cors(env) } });
  },
};
