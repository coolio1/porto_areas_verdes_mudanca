import { consumir } from "./limites.ts";
export { Contador } from "./contador.ts";
import { verificarTurnstile } from "./turnstile.ts";
import { montarMensagens, type Chunk } from "./prompt.ts";
import { keyParaFonte } from "./fontes.ts";
import { deltaDe, ValidadorFluxo } from "./stream.ts";

const MODELO = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";
const MAX_PERGUNTA = 500;
const LIMIAR = 0.4;
const MAX_EXCERTOS = 12;
const MAX_CARACTERES = 36000; // ~10 mil tokens de excertos, deixa folga para prompt e resposta

type Env = any; // sem @cloudflare/workers-types (node_modules fora do OneDrive)

function cors(env: Env): Record<string, string> {
  return { "access-control-allow-origin": env.ORIGEM_PERMITIDA, "access-control-allow-methods": "POST, OPTIONS", "access-control-allow-headers": "content-type", "access-control-max-age": "86400", vary: "origin" };
}
function erro(env: Env, codigo: string, status: number): Response {
  return new Response(JSON.stringify({ erro: codigo }), { status, headers: { "content-type": "application/json", ...cors(env) } });
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    if (req.headers.get("origin") !== env.ORIGEM_PERMITIDA) return new Response("origem não permitida", { status: 403 });
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(env) });
    if (req.method !== "POST") return erro(env, "metodo", 405);

    if (!env.SALT) return erro(env, "indisponivel", 503); // sem sal o hash do IP seria reversível
    let corpo: { pergunta?: unknown; token?: unknown };
    try {
      corpo = await req.json();
    } catch {
      return erro(env, "vazia", 400);
    }
    if (!corpo || typeof corpo !== "object") return erro(env, "vazia", 400);
    const pergunta = typeof corpo.pergunta === "string" ? corpo.pergunta.trim() : "";
    if (!pergunta) return erro(env, "vazia", 400);
    if (pergunta.length > MAX_PERGUNTA) return erro(env, "longa", 400);

    const ip = req.headers.get("cf-connecting-ip") ?? "0.0.0.0";
    const ts = await verificarTurnstile(String(corpo.token ?? ""), ip, env.TURNSTILE_SECRET);
    if (ts === "erro") return erro(env, "indisponivel", 503);
    if (!ts) return erro(env, "turnstile", 400);

    let c: "ok" | "limite_dia" | "tecto_mes";
    try {
      c = await consumir(env, ip);
    } catch {
      return erro(env, "indisponivel", 503);
    }
    if (c !== "ok") return erro(env, c, c === "limite_dia" ? 429 : 503);

    let chunks: Chunk[];
    try {
      const r = await env.AI_SEARCH.get("nota-habitacao").search({
        query: pergunta,
        ai_search_options: { retrieval: { max_num_results: MAX_EXCERTOS, match_threshold: LIMIAR } },
      });
      let total = 0;
      chunks = (r.chunks ?? [])
        .filter((x: Chunk) => x.score >= LIMIAR)
        .filter((x: Chunk) => (total += x.text.length) <= MAX_CARACTERES); // o contexto do modelo tem 24 mil tokens
    } catch {
      return erro(env, "indisponivel", 503);
    }
    if (chunks.length === 0) {
      return new Response(JSON.stringify({ erro: "sem_fontes" }), { status: 200, headers: { "content-type": "application/json", ...cors(env) } });
    }

    let origem: ReadableStream;
    try {
      origem = await env.AI.run(MODELO, { messages: montarMensagens(pergunta, chunks), stream: true, max_tokens: 900, temperature: 0.1 });
    } catch (e) {
      // neurónios do dia esgotados: só repõem às 00:00 UTC, não vale "tente daqui a pouco"
      return erro(env, /allocation|neurons/i.test(String((e as Error)?.message)) ? "limite_servico" : "indisponivel", 503);
    }

    const fontes = chunks.map((ch, i) => {
      const chave = ch.item?.key ?? "";
      const f = keyParaFonte(chave);
      return { n: i + 1, titulo: f?.titulo ?? chave, url: f?.url ?? null };
    });
    const validos = new Set(fontes.map((f) => f.n));
    const val = new ValidadorFluxo(validos);
    const enc = new TextEncoder();
    const dec = new TextDecoder();
    const emitir = (t: string) => (t ? enc.encode(`data: ${JSON.stringify({ t })}\n\n`) : null);

    const leitor = origem.getReader();
    const saida = new ReadableStream({
      cancel() {
        return leitor.cancel();
      },
      async start(ctrl) {
        ctrl.enqueue(enc.encode(`event: fontes\ndata: ${JSON.stringify(fontes)}\n\n`));
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
          resto += dec.decode();
          for (const l of resto.split("\n")) {
            if (!l.startsWith("data:")) continue;
            const d = l.slice(5).trim();
            if (d === "[DONE]") continue;
            const e2 = emitir(val.push(deltaDe(d)));
            if (e2) ctrl.enqueue(e2);
          }
          const e = emitir(val.fim());
          if (e) ctrl.enqueue(e);
          ctrl.enqueue(enc.encode("data: [FIM]\n\n"));
        } catch {
          ctrl.enqueue(enc.encode(`event: erro\ndata: {"erro":"indisponivel"}\n\n`));
        }
        try {
          ctrl.close();
        } catch {
          /* já cancelado pelo cliente */
        }
      },
    });
    return new Response(saida, { headers: { "content-type": "text/event-stream", "cache-control": "no-cache", ...cors(env) } });
  },
};
