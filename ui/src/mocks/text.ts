export const messyText = `SAGE — Montreal\n\nThis is    a sample    string with   "smart quotes", zero\u200bwidth spaces, and---broken—dashes.\nLinewraps are inconsistent;some sentences run together.`;

export const normalizedText = `SAGE - Montreal\n\nThis is a sample string with "smart quotes", zero width spaces removed, and—balanced dashes.\nLine wraps are consistent; some sentences run together.`;

export function normalizeText(
  input: string,
  options: { smartQuotes?: boolean; dashes?: boolean; zeroWidth?: boolean; linewrap?: boolean },
) {
  let output = input;
  if (options.smartQuotes) {
    const doubleQuote = String.fromCharCode(34);
    const singleQuote = String.fromCharCode(39);
    output = output.replace(/[“”]/g, doubleQuote).replace(/[‘’]/g, singleQuote);
  }
  if (options.dashes) {
    output = output.replace(/---/g, '—').replace(/--/g, '–');
  }
  if (options.zeroWidth) {
    output = output.replace(/[\u200B-\u200D\uFEFF]/g, '');
  }
  if (options.linewrap) {
    output = output.replace(/\s+/g, ' ');
  }
  return output.trim();
}
