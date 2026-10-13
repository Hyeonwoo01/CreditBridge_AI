export interface Token {
  stem: string;
  start: number;
  end: number;
}

/** 아주 가벼운 영어 어간 정규화 — 단·복수 차이만 흡수한다. */
export function stem(word: string): string {
  const w = word.toLowerCase().replace(/['’]/g, '');
  if (w.length <= 3) return w;
  if (w.endsWith('ies') && w.length > 4) return w.slice(0, -3) + 'y';
  if (w.endsWith('sses')) return w.slice(0, -2);
  if (w.endsWith('ss')) return w;
  if (/(ches|shes|xes|zes)$/.test(w)) return w.slice(0, -2);
  if (w.endsWith('s') && !w.endsWith('us') && !w.endsWith('is')) return w.slice(0, -1);
  return w;
}

export function tokenize(text: string): Token[] {
  const out: Token[] = [];
  const re = /[A-Za-z0-9]+(?:['’][A-Za-z]+)?/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    out.push({ stem: stem(m[0]), start: m.index, end: m.index + m[0].length });
  }
  return out;
}

const phraseCache = new Map<string, string[]>();

export function phraseStems(phrase: string): string[] {
  let stems = phraseCache.get(phrase);
  if (!stems) {
    stems = tokenize(phrase).map((t) => t.stem);
    phraseCache.set(phrase, stems);
  }
  return stems;
}

/** 토큰 배열 안에서 구(phrase)가 등장하는 모든 위치(토큰 인덱스)를 찾는다. */
export function findPhrase(tokens: Token[], phrase: string): number[] {
  const p = phraseStems(phrase);
  if (p.length === 0) return [];
  const hits: number[] = [];
  outer: for (let i = 0; i + p.length <= tokens.length; i++) {
    for (let j = 0; j < p.length; j++) {
      if (tokens[i + j].stem !== p[j]) continue outer;
    }
    hits.push(i);
  }
  return hits;
}

export interface TextPart {
  text: string;
  mark: boolean;
}

/** 근거 구절 하이라이트용: 키워드가 등장한 구간을 mark=true로 쪼갠다. */
export function highlight(text: string, keywords: string[]): TextPart[] {
  const tokens = tokenize(text);
  const ranges: [number, number][] = [];
  for (const kw of keywords) {
    const len = phraseStems(kw).length;
    for (const i of findPhrase(tokens, kw)) {
      ranges.push([tokens[i].start, tokens[i + len - 1].end]);
    }
  }
  if (ranges.length === 0) return [{ text, mark: false }];
  ranges.sort((a, b) => a[0] - b[0]);
  const merged: [number, number][] = [];
  for (const r of ranges) {
    const last = merged[merged.length - 1];
    if (last && r[0] <= last[1] + 1) last[1] = Math.max(last[1], r[1]);
    else merged.push([...r]);
  }
  const parts: TextPart[] = [];
  let pos = 0;
  for (const [s, e] of merged) {
    if (s > pos) parts.push({ text: text.slice(pos, s), mark: false });
    parts.push({ text: text.slice(s, e), mark: true });
    pos = e;
  }
  if (pos < text.length) parts.push({ text: text.slice(pos), mark: false });
  return parts;
}

/** [3,4,5,8] → "3–5, 8주차" */
export function summarizeWeeks(weeks: number[]): string | null {
  const sorted = [...new Set(weeks)].sort((a, b) => a - b);
  if (sorted.length === 0) return null;
  const groups: string[] = [];
  let start = sorted[0];
  let prev = sorted[0];
  for (const w of [...sorted.slice(1), Infinity]) {
    if (w === prev + 1) {
      prev = w;
      continue;
    }
    groups.push(start === prev ? `${start}` : `${start}–${prev}`);
    start = prev = w;
  }
  return `${groups.join(', ')}주차`;
}
