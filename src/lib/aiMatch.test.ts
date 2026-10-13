import { describe, expect, it } from 'vitest';
import { buildEvaluationPrompt, candidatesFromEvaluation, validateEvaluation } from './aiMatch';
import { extractLocally } from './extract';
import { matchCourse } from './match';
import { SAMPLES } from '../data/samples';
import { getUniversity } from '../data/catalog';
import type { MyCourse } from './types';

const school = getUniversity('berkeley');

function course(text: string): MyCourse {
  return { id: 'c', createdAt: 0, fileName: 'f', rawText: text, parsed: extractLocally(text), source: 'local', grade: '' };
}

const calc = course(SAMPLES.find((s) => s.id === 'calc')!.text);

describe('buildEvaluationPrompt', () => {
  it('includes the catalog objectives and the syllabus', () => {
    const prompt = buildEvaluationPrompt(calc, school);
    expect(prompt).toContain('MATH 1A');
    expect(prompt).toContain('product, quotient and chain rules');
    expect(prompt).toContain('Week 6: The chain rule, implicit differentiation');
  });
});

describe('validateEvaluation', () => {
  const raw = {
    candidates: [
      {
        code: 'math 1a',
        level: 'same',
        levelNote: '',
        summary: '미적분 I과 같은 내용이에요.',
        units: [
          { unit: 'Derivatives', coverage: 95, evidence: [{ where: 'Week 6', quote: 'The chain rule,  implicit differentiation' }], reason: 'r' },
          { unit: 'Integration', coverage: 90, evidence: [{ where: 'Week 14', quote: 'Integration by parts and partial fractions' }], reason: 'r' },
          { unit: 'Limits & Continuity', coverage: 250, evidence: [{ where: 'Week 2', quote: 'The limit of a function, one-sided limits' }], reason: 'r' },
        ],
      },
      { code: 'NOT 999', level: 'same', units: [] },
    ],
  };

  it('keeps verbatim quotes and drops fabricated ones', () => {
    const ev = validateEvaluation(raw, calc, school);
    expect(ev.candidates).toHaveLength(1);
    const [c] = ev.candidates;
    expect(c.code).toBe('MATH 1A');
    const by = Object.fromEntries(c.units.map((u) => [u.unit, u]));
    expect(by['Derivatives'].evidence).toHaveLength(1);
    expect(by['Derivatives'].coverage).toBe(95);
    // 원문에 없는 인용 → 근거 없음 → 점수 상한
    expect(by['Integration'].evidence).toHaveLength(0);
    expect(by['Integration'].coverage).toBe(40);
    expect(by['Limits & Continuity'].coverage).toBe(100);
    // 응답에 빠진 단원은 0점
    expect(by['Applications of Derivatives'].coverage).toBe(0);
  });

  it('discounts a lower-level course even when content overlaps', () => {
    const same = validateEvaluation(raw, calc, school);
    const lower = validateEvaluation({ candidates: [{ ...raw.candidates[0], level: 'lower', levelNote: '경영 미적분' }] }, calc, school);
    const a = candidatesFromEvaluation(same, calc, school)[0];
    const b = candidatesFromEvaluation(lower, calc, school)[0];
    expect(b.score).toBeCloseTo(a.score * 0.75);
    expect(b.warnings[0]).toBe('경영 미적분');
    expect(a.units.find((u) => u.unit.name === 'Derivatives')!.weekRange).toBe('6주차');
  });

  it('survives garbage input', () => {
    expect(validateEvaluation(null, calc, school).candidates).toEqual([]);
    expect(validateEvaluation({ candidates: 'x' }, calc, school).candidates).toEqual([]);
  });
});

describe('keyword fallback', () => {
  it('caps topics that are only mentioned in the overview', () => {
    const businessMath = course(`Riverside College
BUS 105 Business Mathematics
3 credits

Course Description
A survey of mathematics for business. Students preview how derivatives, limits and optimization appear in economics, without formal calculus.

Weekly Schedule
Week 1: Percentages and markups
Week 2: Simple and compound interest
Week 3: Annuities and loans
Week 4: Payroll and taxes
Week 5: Linear equations for break-even analysis`);
    const result = matchCourse(businessMath, school);
    const calc1 = result.candidates.find((c) => c.course.code === 'MATH 1A');
    expect(calc1 === undefined || calc1.score < 0.4).toBe(true);
    for (const u of calc1?.units ?? []) expect(u.coverage).toBeLessThanOrEqual(0.5);
  });
});
