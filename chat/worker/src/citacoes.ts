/** Remove de `texto` as citações [n] ou [n, m] cujo n não esteja em `validos`. */
export function validarCitacoes(texto: string, validos: Set<number>): string {
  return texto.replace(/\s?\[(\d+(?:\s*[,;]\s*\d+)*)\]/g, (todo, lista: string) => {
    const bons = lista.split(/[,;]/).map((x) => Number(x.trim())).filter((n) => validos.has(n));
    if (bons.length === 0) return "";
    const espaco = todo.startsWith(" ") ? " " : "";
    return `${espaco}[${bons.join(", ")}]`;
  });
}
