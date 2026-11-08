export const LIMITE_DIA = 10;
export const TECTO_MES = 950; // o gratuito dá 1 000 consultas/mês; margem de 50

type KV = {
  get(k: string): unknown;
  put(k: string, v: unknown): void;
  delete(k: string): void;
  list(o: { prefix: string }): Iterable<[string, unknown]>;
};

/** Contagem síncrona (atómica dentro de um Durable Object: sem await entre ler e escrever). */
export function contar(kv: KV, h: string, agoraISO: string): "ok" | "limite_dia" | "tecto_mes" {
  const dia = agoraISO.slice(0, 10);
  const mes = agoraISO.slice(0, 7);
  if (kv.get("dia") !== dia) {
    for (const [k] of [...kv.list({ prefix: "d:" })]) kv.delete(k); // só interessa o dia de hoje
    kv.put("dia", dia);
  }
  const nMes = Number(kv.get(`m:${mes}`) ?? 0);
  const nDia = Number(kv.get(`d:${h}`) ?? 0);
  if (nMes >= TECTO_MES) return "tecto_mes";
  if (nDia >= LIMITE_DIA) return "limite_dia";
  kv.put(`d:${h}`, nDia + 1);
  kv.put(`m:${mes}`, nMes + 1);
  return "ok";
}

/** Durable Object (SQLite): um único, "global". Guarda só hashes de IP do dia e o total do mês. */
export class Contador {
  ctx: { storage: { kv: KV } };
  constructor(ctx: { storage: { kv: KV } }) {
    this.ctx = ctx;
  }
  async fetch(req: Request): Promise<Response> {
    const { h } = (await req.json()) as { h: string };
    return new Response(JSON.stringify({ r: contar(this.ctx.storage.kv, h, new Date().toISOString()) }));
  }
}
