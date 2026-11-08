/** true/false = veredicto da Cloudflare; "erro" = não foi possível perguntar (rede). */
export async function verificarTurnstile(token: string, ip: string, secret: string): Promise<boolean | "erro"> {
  try {
    const f = new FormData();
    f.append("secret", secret);
    f.append("response", token);
    f.append("remoteip", ip);
    const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body: f });
    const j = (await r.json()) as { success?: boolean; "error-codes"?: string[]; hostname?: string };
    if (j.success !== true) console.log("turnstile recusado", JSON.stringify({ codigos: j["error-codes"], hostname: j.hostname, tokenLen: token.length, segredoLen: (secret ?? "").length }));
    return j.success === true;
  } catch {
    return "erro";
  }
}
