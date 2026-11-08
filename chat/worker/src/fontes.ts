import refs from "../../refs.json" with { type: "json" };

export type Fonte = { id: string; titulo: string; url: string };

const NOTA_URL = "https://portoverde.pt/posts/habitacao-lisboa-porto/";

/** Converte a chave do ficheiro no índice (refNNN.md, nota_NN_*.md) numa fonte citável. */
export function keyParaFonte(key: string): Fonte | null {
  const r = /^ref(\d{3})\.md$/.exec(key);
  if (r) {
    const e = (refs.refs as Record<string, { t: string; u: string }>)[String(Number(r[1]))];
    return e ? { id: `ref${r[1]}`, titulo: e.t, url: e.u } : null;
  }
  const n = /^nota_(\d{2})_/.exec(key);
  if (n) {
    const t = (refs.nota as Record<string, string>)[n[1]];
    return t ? { id: `nota_${n[1]}`, titulo: `Nota, secção «${t}»`, url: NOTA_URL } : null;
  }
  return null;
}
