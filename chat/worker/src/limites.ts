export const LIMITE_DIA = 10;
export const TECTO_MES = 950; // o gratuito dá 1 000 consultas/mês; margem de 50

type KV = { get(k: string): Promise<string | null>; put(k: string, v: string, o?: { expirationTtl: number }): Promise<void> };

async function sha256(s: string): Promise<string> {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

/** Verifica e regista uma pergunta. O IP nunca é guardado: só o hash com sal diário. */
export async function consumir(env: { LIMITES: KV; SALT?: string }, ip: string): Promise<"ok" | "limite_dia" | "tecto_mes"> {
  const agora = new Date().toISOString();
  const dia = agora.slice(0, 10);
  const mes = agora.slice(0, 7);
  const chaveDia = `d:${(await sha256(`${ip}|${dia}|${env.SALT ?? ""}`)).slice(0, 32)}`;
  const nDia = Number((await env.LIMITES.get(chaveDia)) ?? 0);
  const nMes = Number((await env.LIMITES.get(`m:${mes}`)) ?? 0);
  if (nMes >= TECTO_MES) return "tecto_mes";
  if (nDia >= LIMITE_DIA) return "limite_dia";
  await env.LIMITES.put(chaveDia, String(nDia + 1), { expirationTtl: 90000 });
  await env.LIMITES.put(`m:${mes}`, String(nMes + 1));
  return "ok";
}
