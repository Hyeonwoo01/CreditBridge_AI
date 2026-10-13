import type { ParsedSyllabus, SyllabusWeek } from './types';

/**
 * AI 서버를 쓸 수 없을 때를 위한 규칙 기반 강의계획서 파서.
 * 흔한 영문 Syllabus 양식(섹션 제목 + 주차별 일정)을 가정한다.
 */

type Section = 'description' | 'outcomes' | 'schedule' | 'textbooks' | 'prerequisites' | 'assessments' | 'other';

const SECTION_PATTERNS: [Section, RegExp][] = [
  ['outcomes', /^(student\s+)?(learning\s+)?(outcomes?|objectives?|goals?)\b|^course\s+(objectives?|goals?|outcomes?)|학습\s*목표/i],
  ['description', /^(course\s+)?(description|overview)\b|^about\s+(this|the)\s+course|강의\s*개요/i],
  ['schedule', /^(course\s+|tentative\s+|weekly\s+|class\s+)?(schedule|outline|calendar|topics)\b|주차별|강의\s*일정/i],
  ['textbooks', /^(required\s+|recommended\s+)?(textbooks?|texts?|materials|readings?|course\s+materials)\b|교재/i],
  ['prerequisites', /^(pre-?requisites?|co-?requisites?)\b|선수\s*과목/i],
  ['assessments', /^(grading|assessments?|evaluation|grade\s+breakdown|course\s+grade)\b|평가/i],
  ['other', /^(attendance|office hours|instructor|contact|policies|academic integrity|accommodations?|disability|late work|exams?\s+policy)\b/i],
];

const WEEK_LINE =
  /^(?:week|wk|lecture|session|module|unit|class)s?\s*\.?\s*(\d{1,2})(?:\s*(?:-|–|&|,|and|to)\s*(\d{1,2}))?\s*[:.)\-–—]?\s*(.*)$/i;
const KO_WEEK_LINE = /^(\d{1,2})\s*주\s*차?\s*[:.)\-–—]?\s*(.*)$/;
const NUMBERED_LINE = /^(\d{1,2})[.)]?\s+(.{4,})$/;

function detectSection(line: string): { section: Section; rest: string } | null {
  if (line.length > 70) return null;
  for (const [section, re] of SECTION_PATTERNS) {
    const m = line.match(re);
    if (m) {
      const rest = line.slice(m.index! + m[0].length).replace(/^[\s:.\-–—]+/, '').trim();
      return { section, rest };
    }
  }
  return null;
}

function cleanBullet(line: string): string {
  return line.replace(/^[\s•▪◦●\-*–—·]+/, '').replace(/^\(?[a-z0-9]{1,2}[.)]\s+/i, '').trim();
}

function findCode(text: string): string {
  const m = text.match(/\b([A-Z]{2,7})\s?-?(\d{2,4}[A-Z]{0,2})\b/);
  return m ? `${m[1]} ${m[2]}` : '';
}

function findCredits(text: string): number | null {
  const patterns = [
    /(?:credits?|units?|credit\s+hours?|semester\s+hours?)\s*[:\-]?\s*(\d+(?:\.\d)?)/i,
    /(\d+(?:\.\d)?)\s*(?:credits?|units?|credit\s+hours?|semester\s+hours?|학점)\b/i,
    /(\d+(?:\.\d)?)\s*학점/,
  ];
  for (const re of patterns) {
    const m = text.match(re);
    if (m) {
      const n = Number(m[1]);
      if (n > 0 && n <= 10) return n;
    }
  }
  return null;
}

function findTitle(lines: string[], code: string): string {
  for (const line of lines.slice(0, 15)) {
    const m = line.match(/^(?:course\s+)?(?:title|name)\s*[:\-]\s*(.+)$/i);
    if (m) return m[1].trim();
  }
  if (code) {
    const codeLine = lines.slice(0, 15).find((l) => l.replace(/\s|-/g, '').includes(code.replace(/\s/g, '')));
    if (codeLine) {
      const rest = codeLine
        .replace(new RegExp(code.replace(' ', '\\s?-?'), 'i'), '')
        .replace(/syllabus/i, '')
        .replace(/^[\s:.\-–—|]+|[\s:.\-–—|]+$/g, '')
        .trim();
      if (rest.length > 3) return rest;
    }
  }
  const first = lines.find((l) => l.length > 3 && l.length < 90 && !/syllabus$/i.test(l) && !/university|college/i.test(l));
  return first ?? 'Untitled course';
}

function findInstitution(lines: string[]): string {
  const line = lines.slice(0, 20).find((l) => /\b(university|college|institute|school of)\b|대학교/i.test(l) && l.length < 90);
  if (!line) return '';
  const m = line.match(/([A-Z][\w.&'\- ]*?(?:University|College|Institute)(?: of [A-Z][\w ]+)?)/);
  return (m ? m[1] : line).trim();
}

export function extractLocally(text: string): ParsedSyllabus {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.replace(/\s+/g, ' ').trim())
    .filter(Boolean);

  const code = findCode(lines.slice(0, 20).join('\n'));
  const buckets: Record<Section, string[]> = {
    description: [],
    outcomes: [],
    schedule: [],
    textbooks: [],
    prerequisites: [],
    assessments: [],
    other: [],
  };
  const weeks: SyllabusWeek[] = [];
  let current: Section | null = null;

  for (const line of lines) {
    const week = line.match(WEEK_LINE);
    const koWeek = line.match(KO_WEEK_LINE);
    if (week && week[3]) {
      const label = week[2] ? `Weeks ${week[1]}-${week[2]}` : `Week ${week[1]}`;
      weeks.push({ label, topic: week[3].trim() });
      current = 'schedule';
      continue;
    }
    if (koWeek && koWeek[2]) {
      weeks.push({ label: `${koWeek[1]}주차`, topic: koWeek[2].trim() });
      current = 'schedule';
      continue;
    }
    const sec = detectSection(line);
    if (sec) {
      current = sec.section;
      if (sec.rest) buckets[current].push(sec.rest);
      continue;
    }
    if (current === 'schedule') {
      const n = line.match(NUMBERED_LINE);
      if (n) {
        weeks.push({ label: `Week ${n[1]}`, topic: n[2].trim() });
        continue;
      }
    }
    if (current) buckets[current].push(line);
  }

  const description = buckets.description.join(' ');
  const outcomes = buckets.outcomes.map(cleanBullet).filter((l) => l.length > 8 && !/^(upon|by the end|students will be able)/i.test(l));
  const textbooks = buckets.textbooks.map(cleanBullet).filter((l) => l.length > 5).slice(0, 5);
  const prerequisites = buckets.prerequisites.map(cleanBullet).filter(Boolean).slice(0, 5);
  const assessments = [...buckets.assessments, ...lines.filter((l) => /\d+\s*%/.test(l) && l.length < 80)]
    .map(cleanBullet)
    .filter((l, i, arr) => l && arr.indexOf(l) === i && /%/.test(l))
    .slice(0, 8);

  // 일정 섹션이 줄글로만 되어 있으면 그 줄들을 주제로 사용한다.
  if (weeks.length === 0 && buckets.schedule.length) {
    buckets.schedule.slice(0, 20).forEach((topic, i) => weeks.push({ label: `Week ${i + 1}`, topic: cleanBullet(topic) }));
  }

  return {
    title: findTitle(lines, code),
    code,
    institution: findInstitution(lines),
    credits: findCredits(text),
    description,
    outcomes,
    weeks,
    textbooks,
    prerequisites,
    assessments,
    keyTopics: [],
  };
}
