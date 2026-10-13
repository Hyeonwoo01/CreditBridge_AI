import { isPassingGrade, likelihoodOf } from './match';
import { summarizeWeeks } from './text';
import type {
  AiCourseJudgment,
  AiEvaluation,
  AiUnitJudgment,
  CandidateMatch,
  EvidenceSegment,
  MyCourse,
  UnitMatch,
  University,
} from './types';

/**
 * Claude에게 "단어가 같은가"가 아니라 "가르치는 내용이 같은가"를 판단하게 한다.
 * 프롬프트와 응답 검증은 공개 페이지(sample)와 서버(/api/evaluate)가 함께 쓴다.
 */

const MAX_SYLLABUS_CHARS = 120_000;

export function buildEvaluationPrompt(course: MyCourse, school: University): string {
  const catalog = school.courses.map((c) => ({
    code: c.code,
    title: c.title,
    credits: c.credits,
    level: c.level,
    units: c.units.map((u) => ({ unit: u.name, objectives: u.objectives })),
  }));
  const syllabus =
    course.rawText.length <= MAX_SYLLABUS_CHARS ? course.rawText : JSON.stringify(course.parsed, null, 1);

  return `You are a transfer-credit evaluator at ${school.name}. Decide which ${school.name} courses the student's prior course is equivalent to, based on what is actually taught.

Judge instructional content, not vocabulary:
- A unit objective counts only if the syllabus devotes class time, assignments, or stated learning outcomes to it. A topic that is only mentioned (a prerequisite, a "review of", a preview, a course-policy sentence, a word inside another phrase such as "homework") does not count.
- Shared words at a different depth or in a different discipline do not count: "derivatives" in a business-math survey is not calculus derivatives; "functions" in a programming course is not mathematical functions; "work" in a writing course is not physics work.
- Compare depth: 100 = the unit's objectives are taught at comparable depth; about 50 = covered briefly or only some objectives; 0 = not taught.
- level: "lower" when the prior course is a less rigorous version of the target (e.g. algebra-based vs calculus-based physics, applied/business calculus vs STEM calculus, a non-majors survey vs a majors course); "higher" when it is more advanced; otherwise "same".
- evidence: for every unit with coverage above 0, give 1-3 quotes copied character-for-character from the syllabus (each under 200 characters) and where they appear ("Week 5", "Learning outcome", "Course description"). Never paraphrase inside a quote.
- reason, levelNote and summary are short sentences in Korean for the student.

Return up to 3 candidate courses from the catalog that could plausibly be equivalent, best first. Return an empty list if none are. Include every unit of each candidate.

Reply with only JSON of this shape:
{"candidates":[{"code":"MATH 1A","level":"same","levelNote":"...","summary":"...","units":[{"unit":"Derivatives","coverage":90,"evidence":[{"where":"Week 5","quote":"..."}],"reason":"..."}]}]}

<catalog school="${school.name}">
${JSON.stringify(catalog)}
</catalog>

<prior_course credits="${course.parsed.credits ?? 'unknown'}">
${syllabus}
</prior_course>`;
}

function norm(s: string): string {
  return s
    .toLowerCase()
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[–—]/g, '-')
    .replace(/\s+/g, ' ')
    .trim();
}

const str = (v: unknown) => (typeof v === 'string' ? v.trim() : '');

/** 근거 없이 높게 준 점수는 믿지 않는다. */
const UNVERIFIED_CAP = 40;

/**
 * 모델 응답을 검증한다: 카탈로그에 없는 과목·단원은 버리고,
 * 인용문이 실제 강의계획서에 없으면 근거에서 제외한다.
 */
export function validateEvaluation(raw: unknown, course: MyCourse, school: University): AiEvaluation {
  const haystack = norm(course.rawText);
  const list = Array.isArray((raw as { candidates?: unknown })?.candidates)
    ? ((raw as { candidates: unknown[] }).candidates as Record<string, unknown>[])
    : [];

  const candidates: AiCourseJudgment[] = [];
  for (const c of list.slice(0, 3)) {
    const target = school.courses.find((x) => norm(x.code) === norm(str(c?.code)));
    if (!target || candidates.some((x) => x.code === target.code)) continue;
    const rawUnits = Array.isArray(c.units) ? (c.units as Record<string, unknown>[]) : [];

    const units: AiUnitJudgment[] = target.units.map((u) => {
      const r = rawUnits.find((x) => norm(str(x?.unit)) === norm(u.name));
      const evidence = (Array.isArray(r?.evidence) ? (r.evidence as Record<string, unknown>[]) : [])
        .map((e) => ({ where: str(e?.where) || '강의계획서', quote: str(e?.quote) }))
        .filter((e) => e.quote.length >= 4 && haystack.includes(norm(e.quote)))
        .slice(0, 3);
      let coverage = Math.max(0, Math.min(100, Number(r?.coverage) || 0));
      if (evidence.length === 0) coverage = Math.min(coverage, UNVERIFIED_CAP);
      return { unit: u.name, coverage, evidence, reason: str(r?.reason) };
    });

    const level = c.level === 'lower' || c.level === 'higher' ? c.level : 'same';
    candidates.push({ code: target.code, level, levelNote: str(c.levelNote), summary: str(c.summary), units });
  }
  return { evaluatedAt: Date.now(), candidates };
}

/** 하위 수준 과목은 내용이 겹쳐도 그대로 인정되기 어렵다. */
const LOWER_LEVEL_FACTOR = 0.75;

function weekOf(where: string): number | null {
  const m = where.match(/(?:week|wk|주)\D{0,3}(\d{1,2})|^(\d{1,2})\s*주차/i);
  return m ? Number(m[1] ?? m[2]) : null;
}

export function candidatesFromEvaluation(ev: AiEvaluation, course: MyCourse, school: University): CandidateMatch[] {
  const out: CandidateMatch[] = [];
  for (const j of ev.candidates) {
    const target = school.courses.find((c) => c.code === j.code);
    if (!target) continue;

    const units: UnitMatch[] = target.units.map((u) => {
      const r = j.units.find((x) => x.unit === u.name);
      const evidence: EvidenceSegment[] = (r?.evidence ?? []).map((e) => {
        const week = weekOf(e.where);
        return { where: week !== null ? `${week}주차` : e.where, week, text: e.quote, matchedKeywords: [], quote: true };
      });
      return {
        unit: u,
        coverage: (r?.coverage ?? 0) / 100,
        matchedKeywords: [],
        evidence,
        weekRange: summarizeWeeks(evidence.map((e) => e.week).filter((w): w is number => w !== null)),
        reason: r?.reason,
      };
    });

    const contentScore = units.reduce((sum, u) => sum + u.coverage, 0) / units.length;
    const score = j.level === 'lower' ? contentScore * LOWER_LEVEL_FACTOR : contentScore;

    const warnings: string[] = [];
    if (j.level === 'lower') warnings.push(j.levelNote || `${target.code}보다 낮은 수준의 과목으로 판단돼요.`);
    const credits = course.parsed.credits;
    if (credits !== null && credits < target.credits) {
      warnings.push(`전적 과목은 ${credits}학점, ${target.code}는 ${target.credits} ${school.creditLabel}예요. 학점 차이만큼 부분 인정될 수 있어요.`);
    }
    if (!isPassingGrade(course.grade)) warnings.push(`성적 ${course.grade}는 대부분 대학의 편입 인정 기준(C 이상)에 못 미쳐요.`);
    for (const u of units) {
      if (u.coverage < 0.34) warnings.push(`'${u.unit.nameKo}' 단원은 실제로 가르친 내용이 거의 없어요.`);
    }

    out.push({
      course: target,
      score,
      likelihood: likelihoodOf(score),
      units,
      textbookMatch: null,
      warnings,
      method: 'ai',
      summary: j.summary || undefined,
    });
  }
  return out.sort((a, b) => b.score - a.score);
}
