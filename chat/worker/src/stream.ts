import { validarCitacoes } from "./citacoes.ts";

/** Extrai o texto de um evento SSE do Workers AI (`response`) ou estilo OpenAI (`choices[0].delta.content`). */
export function deltaDe(dados: string): string {
  try {
    const j = JSON.parse(dados);
    return j.response ?? j.choices?.[0]?.delta?.content ?? "";
  } catch {
    return "";
  }
}

/** Valida citações em fluxo: guarda o que pode ainda formar uma citação ("[" aberto, espaço final). */
export class ValidadorFluxo {
  buf = "";
  validos: Set<number>;
  constructor(validos: Set<number>) {
    this.validos = validos;
  }
  push(delta: string): string {
    this.buf += delta;
    let corte = this.buf.length;
    const abre = this.buf.lastIndexOf("[");
    if (abre !== -1 && this.buf.indexOf("]", abre) === -1) corte = abre;
    while (corte > 0 && this.buf[corte - 1] === " ") corte--;
    const saida = validarCitacoes(this.buf.slice(0, corte), this.validos);
    this.buf = this.buf.slice(corte);
    return saida;
  }
  fim(): string {
    const s = validarCitacoes(this.buf, this.validos);
    this.buf = "";
    return s;
  }
}
