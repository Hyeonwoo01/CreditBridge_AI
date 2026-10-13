export interface SyllabusWeek {
  /** 원문의 주차 표기 (예: "Week 3", "Weeks 3-4", "5주차") */
  label: string;
  topic: string;
}

/** 강의계획서에서 추출한 정형 스키마 */
export interface ParsedSyllabus {
  title: string;
  code: string;
  institution: string;
  credits: number | null;
  description: string;
  outcomes: string[];
  weeks: SyllabusWeek[];
  textbooks: string[];
  prerequisites: string[];
  assessments: string[];
  /** 강의가 다루는 핵심 학술 개념 (AI 추출 시에만 채워짐) */
  keyTopics: string[];
}

export type ExtractSource = 'ai' | 'local';

export interface MyCourse {
  id: string;
  createdAt: number;
  fileName: string;
  rawText: string;
  parsed: ParsedSyllabus;
  source: ExtractSource;
  /** 전적 대학 성적 (선택) */
  grade: string;
}

export interface CatalogUnit {
  name: string;
  nameKo: string;
  keywords: string[];
}

export type SubjectArea = 'math' | 'science' | 'cs' | 'social' | 'humanities';

export interface CatalogCourse {
  id: string;
  code: string;
  title: string;
  credits: number;
  area: SubjectArea;
  /** 전공 기초 / 교양 */
  category: 'major' | 'ge';
  description: string;
  units: CatalogUnit[];
  textbooks: string[];
}

export interface University {
  id: string;
  name: string;
  location: string;
  creditLabel: string;
  tuitionPerCredit: number;
  creditsPerSemester: number;
  /** 편입생이 인정받을 수 있는 최대 학점 */
  transferCreditCap: number;
  courses: CatalogCourse[];
}

export interface EvidenceSegment {
  /** "3주차", "학습 목표", "강의 개요" 등 출처 */
  where: string;
  /** 주차 번호 (주차 범위 요약용) */
  week: number | null;
  text: string;
  matchedKeywords: string[];
}

export interface UnitMatch {
  unit: CatalogUnit;
  coverage: number;
  matchedKeywords: string[];
  evidence: EvidenceSegment[];
  /** 예: "3–5주차" */
  weekRange: string | null;
}

export type Likelihood = 'high' | 'medium' | 'low';

export interface CandidateMatch {
  course: CatalogCourse;
  score: number;
  likelihood: Likelihood;
  units: UnitMatch[];
  textbookMatch: string | null;
  warnings: string[];
}

export interface CourseResult {
  candidates: CandidateMatch[];
}
