import { buildEvaluationPrompt, validateEvaluation } from './aiMatch';
import { extractLocally } from './extract';
import type { AiEvaluation, ExtractSource, MyCourse, ParsedSyllabus, University } from './types';

let serverStatus: Promise<boolean> | null = null;

function checkServer(): Promise<boolean> {
  serverStatus ??= fetch('/api/health')
    .then((r) => (r.ok ? r.json() : { ai: false }))
    .then((d: { ai?: boolean }) => Boolean(d.ai))
    .catch(() => false);
  return serverStatus;
}

/** claude.ai 페이지에서 Claude를 부르는 `sample` 기능 (해당 타입만 최소로 선언) */
interface SampleFn {
  json<T = unknown>(input: string, options?: { modelTier?: 'quick' | 'default' | 'complex' }): Promise<T>;
}
interface SampleError {
  code: string;
  message: string;
}

let samplePromise: Promise<SampleFn | null> | null = null;
let sampleBlocked = false;

function getSample(): Promise<SampleFn | null> {
  const claude = (window as { claude?: { use?: (name: string) => Promise<unknown> } }).claude;
  if (!claude?.use) return Promise.resolve(null);
  samplePromise ??= claude
    .use('sample')
    .then((s) => (s as SampleFn | null) ?? null)
    .catch(() => null);
  return samplePromise;
}

/** viewer: claude.ai 페이지의 Claude, server: 로컬 서버의 API 키, null: AI 없음 */
export type AiMode = 'viewer' | 'server' | null;

export async function getAiMode(): Promise<AiMode> {
  if (!sampleBlocked && (await getSample())) return 'viewer';
  if (await checkServer()) return 'server';
  return null;
}

/** AI 서버가 있으면 Claude로, 없거나 실패하면 브라우저 내 규칙 기반 파서로 추출한다. */
export async function extractSyllabus(text: string): Promise<{ parsed: ParsedSyllabus; source: ExtractSource }> {
  if (await checkServer()) {
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

export class AiUnavailableError extends Error {
  constructor(
    message: string,
    /** true면 이번 방문 동안 AI를 다시 시도하지 않는다 */
    readonly permanent: boolean,
  ) {
    super(message);
  }
}

const PERMANENT = new Set(['not_granted', 'sampling_disabled', 'not_declared', 'capability_disabled', 'capability_removed']);

function messageFor(code: string): string {
  switch (code) {
    case 'not_granted':
      return 'Claude 사용을 허용하지 않아 키워드 기반으로 분석했어요.';
    case 'rate_limited':
      return '요청이 많아 잠시 후 다시 시도해 주세요.';
    case 'invalid_json':
    case 'empty_completion':
      return 'AI 응답을 읽지 못했어요. 다시 시도해 주세요.';
    case 'prompt_too_large':
      return '강의계획서가 너무 길어요. 핵심 부분만 붙여넣어 주세요.';
    default:
      return 'AI 분석에 실패했어요. 다시 시도해 주세요.';
  }
}

/** Claude가 강의 내용을 비교한 결과. AI를 쓸 수 없으면 AiUnavailableError를 던진다. */
export async function evaluateCourse(course: MyCourse, school: University): Promise<AiEvaluation> {
  const mode = await getAiMode();
  if (mode === 'viewer') {
    const sample = (await getSample())!;
    try {
      const raw = await sample.json(buildEvaluationPrompt(course, school), { modelTier: 'default' });
      return validateEvaluation(raw, course, school);
    } catch (e) {
      const code = (e as SampleError)?.code ?? 'upstream_error';
      if (PERMANENT.has(code)) sampleBlocked = true;
      throw new AiUnavailableError(messageFor(code), PERMANENT.has(code));
    }
  }
  if (mode === 'server') {
    const res = await fetch('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schoolId: school.id, course: { rawText: course.rawText, parsed: course.parsed } }),
    }).catch(() => null);
    if (!res?.ok) throw new AiUnavailableError(messageFor(res?.status === 429 ? 'rate_limited' : 'upstream_error'), false);
    const { evaluation } = (await res.json()) as { evaluation: unknown };
    return validateEvaluation(evaluation, course, school);
  }
  throw new AiUnavailableError('AI를 사용할 수 없어 키워드 기반으로 분석했어요.', true);
}
