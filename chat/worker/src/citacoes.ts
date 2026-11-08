/** Remove de `texto` as citações [n] ou [n, m] cujo n não esteja em `validos`, e intervalos [n-m] (não validáveis). */
export function validarCitacoes(texto: string, validos: Set<number>): string {
  return texto
    .replace(/[ \t]?\[\d+\s*[-–]\s*\d+\]/g, "")
    .replace(/([ \t]?)\[(\d+(?:\s*[,;]\s*\d+)*)\]/g, (_todo, espaco: string, lista: string) => {
      const bons = lista.split(/[,;]/).map((x) => Number(x.trim())).filter((n) => validos.has(n));
      return bons.length === 0 ? "" : `${espaco}[${bons.join(", ")}]`;
    });
}
