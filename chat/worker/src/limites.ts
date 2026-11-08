type Env = { SALT?: string; CONTADOR: { idFromName(n: string): unknown; get(id: unknown): { fetch(u: string, i: { method: string; body: string }): Promise<Response> } } };

async function sha256(s: string): Promise<string> {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
}

/** IPv6 agrupa-se por /64 (um visitante tem o /64 inteiro); IPv4 fica igual. */
export function chaveIp(ip: string): string {
  if (!ip.includes(":")) return ip;
  const [antes, depois = ""] = ip.split("::");
  const a = antes ? antes.split(":") : [];
  const d = depois ? depois.split(":") : [];
  const grupos = ip.includes("::") ? [...a, ...Array(8 - a.length - d.length).fill("0"), ...d] : a;
  return grupos.slice(0, 4).map((g) => g.toLowerCase().replace(/^0+(?=.)/, "")).join(":");
}

/** Pede ao contador (Durable Object) para verificar e registar uma pergunta. Só guarda o hash (com sal). */
export async function consumir(env: Env, ip: string): Promise<"ok" | "limite_dia" | "tecto_mes"> {
  const h = (await sha256(`${chaveIp(ip)}|${env.SALT ?? ""}`)).slice(0, 32);
  const stub = env.CONTADOR.get(env.CONTADOR.idFromName("global"));
  const r = await stub.fetch("https://contador/consumir", { method: "POST", body: JSON.stringify({ h }) });
  return ((await r.json()) as { r: "ok" | "limite_dia" | "tecto_mes" }).r;
}
