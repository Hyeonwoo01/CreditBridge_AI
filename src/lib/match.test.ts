import { describe, expect, it } from 'vitest';
import { extractLocally } from './extract';
import { matchCourse } from './match';
import { highlight, summarizeWeeks } from './text';
import { SAMPLES } from '../data/samples';
import { getUniversity } from '../data/catalog';
import type { MyCourse } from './types';

function course(sampleId: string, grade = ''): MyCourse {
  const s = SAMPLES.find((x) => x.id === sampleId)!;
  return { id: sampleId, createdAt: 0, fileName: s.fileName, rawText: s.text, parsed: extractLocally(s.text), source: 'local', grade };
}

describe('extractLocally', () => {
  it('pulls the core syllabus fields', () => {
    const p = course('calc').parsed;
    expect(p.code).toBe('MATH 101');
    expect(p.title).toBe('Calculus I');
    expect(p.institution).toBe('Hanbit University');
    expect(p.credits).toBe(3);
    expect(p.weeks).toHaveLength(16);
    expect(p.weeks[2]).toEqual({ label: 'Week 3', topic: 'Continuity, intermediate value theorem, limits at infinity and asymptotes' });
    expect(p.outcomes).toHaveLength(4);
    expect(p.textbooks[0]).toContain('Stewart');
    expect(p.assessments).toContain('Final exam 40%');
  });

  it('handles dash-separated schedules and unit counts', () => {
    const p = course('python').parsed;
    expect(p.code).toBe('CS 110');
    expect(p.credits).toBe(4);
    expect(p.weeks[0].topic).toMatch(/^What is programming/);
  });
});

describe('matchCourse', () => {
  const cases: [string, string, string][] = [
    ['calc', 'berkeley', 'MATH 1A'],
    ['python', 'umich', 'EECS 183'],
    ['chem', 'utaustin', 'CH 301'],
    ['econ', 'berkeley', 'ECON 1'],
  ];

  it.each(cases)('maps %s to the right course at %s', (sample, school, code) => {
    const top = matchCourse(course(sample), getUniversity(school)).candidates[0];
    expect(top.course.code).toBe(code);
  });

  it('scores a full-coverage syllabus as high likelihood with week evidence', () => {
    const top = matchCourse(course('calc'), getUniversity('berkeley')).candidates[0];
    expect(top.likelihood).toBe('high');
    expect(top.textbookMatch).toContain('Stewart');
    const derivatives = top.units.find((u) => u.unit.name === 'Derivatives')!;
    expect(derivatives.weekRange).toContain('4–6');
  });

  it('ranks the second-semester course below the first', () => {
    const { candidates } = matchCourse(course('calc'), getUniversity('umich'));
    const calc2 = candidates.find((c) => c.course.code === 'MATH 116');
    expect(calc2 === undefined || calc2.score < candidates[0].score).toBe(true);
  });

  it('warns about credit gaps and failing grades', () => {
    const top = matchCourse(course('calc', 'D'), getUniversity('berkeley')).candidates[0];
    expect(top.warnings.some((w) => w.includes('3학점'))).toBe(true);
    expect(top.warnings.some((w) => w.includes('성적 D'))).toBe(true);
  });
});

describe('text helpers', () => {
  it('highlights plural and multi-word keywords', () => {
    const parts = highlight('Limits at infinity and the Chain Rule', ['limits at infinity', 'chain rule']);
    expect(parts.filter((p) => p.mark).map((p) => p.text)).toEqual(['Limits at infinity', 'Chain Rule']);
  });

  it('summarizes week ranges', () => {
    expect(summarizeWeeks([5, 3, 4, 8])).toBe('3–5, 8주차');
    expect(summarizeWeeks([])).toBeNull();
  });
});
