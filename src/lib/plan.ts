import { isPassingGrade } from './match';
import type { CandidateMatch, CourseResult, MyCourse, University } from './types';

/** 학교별로 학생이 고른 대체 과목. 값이 'none'이면 "인정 신청 안 함". */
export type Picks = Record<string, string>;

export const pickKey = (schoolId: string, courseId: string) => `${schoolId}:${courseId}`;

export function resolvePick(
  course: MyCourse,
  result: CourseResult | undefined,
  school: University,
  picks: Picks,
): CandidateMatch | null {
  const picked = picks[pickKey(school.id, course.id)];
  if (picked === 'none') return null;
  const candidates = result?.candidates ?? [];
  if (picked) return candidates.find((c) => c.course.id === picked) ?? null;
  const top = candidates[0];
  return top && top.score >= 0.6 ? top : null;
}

export type RowStatus = 'likely' | 'partial' | 'duplicate' | 'grade' | 'none';

export interface PlanRow {
  course: MyCourse;
  match: CandidateMatch | null;
  status: RowStatus;
  credits: number;
}

export interface Plan {
  rows: PlanRow[];
  credits: number;
  capped: boolean;
  semestersSaved: number;
  tuitionSaved: number;
}

export function buildPlan(
  courses: MyCourse[],
  results: Map<string, CourseResult>,
  school: University,
  picks: Picks,
  tuitionPerCredit: number,
): Plan {
  const usedTargets = new Set<string>();
  const rows: PlanRow[] = courses.map((course) => {
    const match = resolvePick(course, results.get(course.id), school, picks);
    if (!match || match.score < 0.6) return { course, match, status: 'none', credits: 0 };
    if (!isPassingGrade(course.grade)) return { course, match, status: 'grade', credits: 0 };
    if (usedTargets.has(match.course.id)) return { course, match, status: 'duplicate', credits: 0 };
    usedTargets.add(match.course.id);
    // 전적 과목 학점이 더 적으면 그만큼만 인정되는 것으로 보수적으로 계산한다.
    const src = course.parsed.credits;
    const credits = src !== null && src < match.course.credits ? src : match.course.credits;
    return { course, match, status: match.likelihood === 'high' ? 'likely' : 'partial', credits };
  });

  const total = rows.reduce((sum, r) => sum + r.credits, 0);
  const credits = Math.min(total, school.transferCreditCap);
  return {
    rows,
    credits,
    capped: total > school.transferCreditCap,
    semestersSaved: Math.round((credits / school.creditsPerSemester) * 10) / 10,
    tuitionSaved: credits * tuitionPerCredit,
  };
}
