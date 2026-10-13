import type { EvalState } from '../App';
import type { CandidateMatch, CourseResult, MyCourse, University } from '../lib/types';
import { CourseTile, LikelihoodBadge } from './common';
import { Chevron, Search } from './Icons';
import { Uploader } from './Uploader';

interface Props {
  school: University;
  schools: University[];
  onSchool: (id: string) => void;
  courses: MyCourse[];
  results: Map<string, CourseResult>;
  picked: (course: MyCourse) => CandidateMatch | null;
  evalOf: (course: MyCourse) => EvalState | undefined;
  busy: string[];
  onAdd: (text: string, fileName: string) => Promise<void>;
  onOpen: (id: string) => void;
}

export function AnalyzeScreen({ school, schools, onSchool, courses, results, picked, evalOf, busy, onAdd, onOpen }: Props) {
  return (
    <div className="screen">
      <header className="hero">
        <h1 className="display-xl">내 과목, 편입하면 인정될까?</h1>
        <p className="muted">강의계획서를 올리면 희망 대학의 어떤 과목으로 인정될지 근거와 함께 알려드려요.</p>
      </header>

      <label className="search-pill">
        <span className="search-segment">
          <span className="caption">편입 희망 대학</span>
          <select value={school.id} onChange={(e) => onSchool(e.target.value)} aria-label="편입 희망 대학">
            {schools.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} · {s.location}
              </option>
            ))}
          </select>
        </span>
        <span className="search-orb" aria-hidden>
          <Search />
        </span>
      </label>

      <Uploader busy={busy} onAdd={onAdd} usedSamples={new Set(courses.map((c) => c.fileName))} />

      {courses.length > 0 && (
        <section className="section">
          <div className="section-head">
            <h2 className="display-sm">내 과목 {courses.length}개</h2>
            <span className="muted body-sm">{school.name} 기준</span>
          </div>
          <div className="card-grid">
            {courses.map((c) => {
              const top = results.get(c.id)?.candidates[0];
              const pick = picked(c);
              const shown = pick ?? top;
              const analyzing = evalOf(c)?.status === 'running';
              return (
                <button key={c.id} className="course-card" onClick={() => onOpen(c.id)}>
                  <CourseTile code={c.parsed.code} area={shown?.course.area ?? null} />
                  <div className="course-card-body">
                    <div className="row-between">
                      <span className="title-md ellipsis">{c.parsed.title}</span>
                      {shown && <span className="score-inline">{Math.round(shown.score * 100)}%</span>}
                    </div>
                    <span className="muted body-sm ellipsis">
                      {[c.parsed.code, c.parsed.institution].filter(Boolean).join(' · ') || c.fileName}
                    </span>
                    {shown ? (
                      <div className="match-line">
                        <span className="body-sm">
                          → <strong>{shown.course.code}</strong> {shown.course.title}
                        </span>
                      </div>
                    ) : (
                      <span className="body-sm muted">비슷한 과목을 찾지 못했어요</span>
                    )}
                    <div className="row-between">
                      {analyzing ? (
                        <span className="badge">
                          <span className="spinner spinner-sm" /> AI가 수업 내용 비교 중
                        </span>
                      ) : shown ? (
                        <LikelihoodBadge likelihood={shown.likelihood} />
                      ) : (
                        <span />
                      )}
                      <Chevron width={16} height={16} className="muted" />
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
