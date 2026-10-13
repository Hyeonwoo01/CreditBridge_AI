import { extractLocally } from './extract';
import type { ExtractSource, ParsedSyllabus } from './types';

let aiStatus: Promise<boolean> | null = null;

export function checkAi(): Promise<boolean> {
  aiStatus ??= fetch('/api/health')
    .then((r) => (r.ok ? r.json() : { ai: false }))
    .then((d: { ai?: boolean }) => Boolean(d.ai))
    .catch(() => false);
  return aiStatus;
}

/** AI 서버가 있으면 Claude로, 없거나 실패하면 브라우저 내 규칙 기반 파서로 추출한다. */
export async function extractSyllabus(text: string): Promise<{ parsed: ParsedSyllabus; source: ExtractSource }> {
  if (await checkAi()) {
    try {
      const res = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (res.ok) {
        const { syllabus } = (await res.json()) as { syllabus: ParsedSyllabus };
        return { parsed: syllabus, source: 'ai' };
      }
    } catch {
      // 네트워크 오류 → 로컬 파서로 대체
    }
  }
  return { parsed: extractLocally(text), source: 'local' };
}
