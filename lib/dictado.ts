/** Une el texto que ya estaba escrito con lo dictado, con un espacio entre medio. */
export function unirDictado(base: string, dictado: string): string {
  const d = dictado.trim();
  if (!d) return base;
  return base && !/\s$/.test(base) ? `${base} ${d}` : `${base}${d}`;
}
