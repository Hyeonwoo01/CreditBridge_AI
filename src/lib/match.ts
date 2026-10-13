import type {
  CandidateMatch,
  CatalogCourse,
  CourseResult,
  EvidenceSegment,
  Likelihood,
  MyCourse,
  ParsedSyllabus,
  UnitMatch,
  University,
} from './types';
import { findPhrase, summarizeWeeks, tokenize, type Token } from './text';

interface Segment {
  where: string;
  week: number | null;
  text: string;
  tokens: Token[];
}

const PASSING_GRADES = new Set(['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'P', '']);

export function isPassingGrade(grade: string): boolean {
  return PASSING_GRADES.has(grade);
}

export function likelihoodOf(score: number): Likelihood {
  if (score >= 0.8) return 'high';
  if (score >= 0.6) return 'medium';
  return 'low';
}

export const LIKELIHOOD_LABEL: Record<Likelihood, string> = {
  high: '인정 가능성 높음',
  medium: '부분 인정 가능',
  low: '인정 어려움',
};

function weekNumber(label: string): number | null {
  const m = label.match(/\d+/);
  return m ? Number(m[0]) : null;
}

function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?;])\s+|\n+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 3);
}

function buildSegments(p: ParsedSyllabus, rawText: string): Segment[] {
  const raw: Omit<Segment, 'tokens'>[] = [];
  for (const w of p.weeks) {
    const n = weekNumber(w.label);
    raw.push({ where: n !== null ? `${n}주차` : w.label, week: n, text: w.topic });
  }
  p.outcomes.forEach((o) => raw.push({ where: '학습 목표', week: null, text: o }));
  splitSentences(p.description).forEach((s) => raw.push({ where: '강의 개요', week: null, text: s }));
  p.keyTopics.forEach((k) => raw.push({ where: '핵심 개념', week: null, text: k }));

  // 구조화된 내용이 거의 없으면 원문 줄 단위로 대신 비교한다.
  if (raw.length < 3) {
    rawText
      .split(/\n+/)
      .map((l) => l.trim())
      .filter((l) => l.length > 3)
      .forEach((l) => raw.push({ where: '원문', week: null, text: l }));
  }
  return raw.map((s) => ({ ...s, tokens: tokenize(s.text) }));
}

/** 키워드 60% 이상이 확인되면 해당 단원은 충분히 다룬 것으로 본다. */
function unitCoverage(matched: number, total: number): number {
  return Math.min(1, matched / Math.max(1, Math.ceil(total * 0.6)));
}

function matchUnits(course: CatalogCourse, segments: Segment[]): UnitMatch[] {
  return course.units.map((unit) => {
    const matched = new Set<string>();
    const evidence: EvidenceSegment[] = [];
    for (const seg of segments) {
      const kws = unit.keywords.filter((kw) => findPhrase(seg.tokens, kw).length > 0);
      if (kws.length === 0) continue;
      kws.forEach((k) => matched.add(k));
      evidence.push({ where: seg.where, week: seg.week, text: seg.text, matchedKeywords: kws });
    }
    evidence.sort((a, b) => b.matchedKeywords.length - a.matchedKeywords.length);
    const weeks = evidence.map((e) => e.week).filter((w): w is number => w !== null);
    return {
      unit,
      coverage: unitCoverage(matched.size, unit.keywords.length),
      matchedKeywords: [...matched],
      evidence: evidence.slice(0, 4),
      weekRange: summarizeWeeks(weeks),
    };
  });
}

function findTextbookMatch(p: ParsedSyllabus, course: CatalogCourse): string | null {
  for (const book of p.textbooks) {
    const lower = book.toLowerCase();
    const hit = course.textbooks.find((t) => lower.includes(t.toLowerCase()));
    if (hit) return book;
  }
  return null;
}

function scoreCourse(
  myCourse: MyCourse,
  course: CatalogCourse,
  segments: Segment[],
  school: University,
): CandidateMatch {
  const units = matchUnits(course, segments);
  // 단원별 충족도(주) + 전체 키워드 커버리지(보조)를 섞어 100%로 쉽게 포화되지 않게 한다.
  const unitScore = units.reduce((sum, u) => sum + u.coverage, 0) / units.length;
  const totalKeywords = course.units.reduce((sum, u) => sum + u.keywords.length, 0);
  const rawScore = units.reduce((sum, u) => sum + u.matchedKeywords.length, 0) / totalKeywords;
  const base = 0.75 * unitScore + 0.25 * rawScore;
  const textbookMatch = base > 0.3 ? findTextbookMatch(myCourse.parsed, course) : null;
  const score = Math.min(1, base + (textbookMatch ? 0.03 : 0));

  const warnings: string[] = [];
  const credits = myCourse.parsed.credits;
  if (credits !== null && credits < course.credits) {
    warnings.push(
      `전적 과목은 ${credits}학점, ${course.code}는 ${course.credits} ${school.creditLabel}예요. 학점 차이만큼 부분 인정될 수 있어요.`,
    );
  }
  if (!isPassingGrade(myCourse.grade)) {
    warnings.push(`성적 ${myCourse.grade}는 대부분 대학의 편입 인정 기준(C 이상)에 못 미쳐요.`);
  }
  for (const u of units) {
    if (u.coverage < 0.34) warnings.push(`'${u.unit.nameKo}' 단원 내용이 강의계획서에서 거의 확인되지 않아요.`);
  }

  return { course, score, likelihood: likelihoodOf(score), units, textbookMatch, warnings };
}

export function matchCourse(myCourse: MyCourse, school: University): CourseResult {
  const segments = buildSegments(myCourse.parsed, myCourse.rawText);
  const candidates = school.courses
    .map((c) => scoreCourse(myCourse, c, segments, school))
    .filter((c) => c.score >= 0.2)
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);
  return { candidates };
}

/** "A대학 3–5주차 내용이 본교 MATH 1A의 '도함수' 단원과 일치" 형태의 요약 문장 */
export function evidenceSentence(myCourse: MyCourse, unit: UnitMatch, course: CatalogCourse): string {
  const school = myCourse.parsed.institution || '전적 대학';
  const where = unit.weekRange ?? unit.evidence[0]?.where ?? '강의계획서';
  return `${school} ${where} 내용이 ${course.code}의 '${unit.unit.nameKo}' 단원과 ${Math.round(unit.coverage * 100)}% 일치`;
}
