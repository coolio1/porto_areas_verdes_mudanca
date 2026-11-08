export async function verificarTurnstile(token: string, ip: string, secret: string): Promise<boolean> {
  try {
    const f = new FormData();
    f.append("secret", secret);
    f.append("response", token);
    f.append("remoteip", ip);
    const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body: f });
    return ((await r.json()) as { success?: boolean }).success === true;
  } catch {
    return false;
  }
}
