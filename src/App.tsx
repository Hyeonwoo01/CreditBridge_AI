import { useCallback, useEffect, useMemo, useState } from 'react';
import { UNIVERSITIES, getUniversity } from './data/catalog';
import { checkAi, extractSyllabus } from './lib/api';
import { matchCourse } from './lib/match';
import { buildPlan, pickKey, resolvePick, type Picks } from './lib/plan';
import type { CourseResult, MyCourse } from './lib/types';
import { useStored } from './lib/useStored';
import { AnalyzeScreen } from './components/AnalyzeScreen';
import { CourseDetail } from './components/CourseDetail';
import { PlanScreen } from './components/PlanScreen';
import { Book, Logo, Plan, Sparkle } from './components/Icons';

type Tab = 'analyze' | 'plan';

export default function App() {
  const [courses, setCourses] = useStored<MyCourse[]>('cb.courses', []);
  const [schoolId, setSchoolId] = useStored('cb.school', UNIVERSITIES[0].id);
  const [picks, setPicks] = useStored<Picks>('cb.picks', {});
  const [tuition, setTuition] = useStored<Record<string, number>>('cb.tuition', {});
  const [tab, setTab] = useState<Tab>('analyze');
  const [openId, setOpenId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string[]>([]);
  const [ai, setAi] = useState(false);

  useEffect(() => {
    void checkAi().then(setAi);
  }, []);

  const school = getUniversity(schoolId);
  const tuitionPerCredit = tuition[school.id] ?? school.tuitionPerCredit;

  const results = useMemo(
    () => new Map<string, CourseResult>(courses.map((c) => [c.id, matchCourse(c, school)])),
    [courses, school],
  );
  const plan = useMemo(() => buildPlan(courses, results, school, picks, tuitionPerCredit), [courses, results, school, picks, tuitionPerCredit]);

  const addCourse = useCallback(
    async (text: string, fileName: string) => {
      setBusy((b) => [...b, fileName]);
      try {
        const { parsed, source } = await extractSyllabus(text);
        const course: MyCourse = { id: crypto.randomUUID(), createdAt: Date.now(), fileName, rawText: text, parsed, source, grade: '' };
        setCourses((prev) => [course, ...prev]);
      } finally {
        setBusy((b) => {
          const i = b.indexOf(fileName);
          return i < 0 ? b : [...b.slice(0, i), ...b.slice(i + 1)];
        });
      }
    },
    [setCourses],
  );

  const open = openId ? courses.find((c) => c.id === openId) : undefined;
  const picked = (c: MyCourse) => resolvePick(c, results.get(c.id), school, picks);
  const closeDetail = useCallback(() => setOpenId(null), []);

  return (
    <div className="app">
      <header className="top-nav">
        <a className="brand" href="/" onClick={(e) => (e.preventDefault(), setTab('analyze'))}>
          <Logo />
          <span>creditbridge</span>
        </a>
        <nav className="product-tabs" aria-label="메인">
          <button className={tab === 'analyze' ? 'active' : ''} onClick={() => setTab('analyze')}>
            과목 분석
          </button>
          <button className={tab === 'plan' ? 'active' : ''} onClick={() => setTab('plan')}>
            내 편입 플랜
            {plan.credits > 0 && <span className="count-tag">{plan.credits}</span>}
          </button>
        </nav>
        <span className={`ai-status${ai ? ' on' : ''}`} title={ai ? 'Claude가 강의계획서를 분석해요' : '브라우저에서 규칙 기반으로 분석해요'}>
          <Sparkle width={14} height={14} /> {ai ? 'AI 분석 켜짐' : '오프라인 분석'}
        </span>
      </header>

      <main>
        {tab === 'analyze' ? (
          <AnalyzeScreen
            school={school}
            schools={UNIVERSITIES}
            onSchool={setSchoolId}
            courses={courses}
            results={results}
            picked={picked}
            busy={busy}
            onAdd={addCourse}
            onOpen={setOpenId}
          />
        ) : (
          <PlanScreen
            plan={plan}
            school={school}
            tuitionPerCredit={tuitionPerCredit}
            onTuition={(v) => setTuition((t) => ({ ...t, [school.id]: v }))}
            onOpen={setOpenId}
            onGoAnalyze={() => setTab('analyze')}
          />
        )}
      </main>

      <nav className="bottom-nav" aria-label="메인">
        <button className={tab === 'analyze' ? 'active' : ''} onClick={() => setTab('analyze')}>
          <Book />
          <span>과목 분석</span>
        </button>
        <button className={tab === 'plan' ? 'active' : ''} onClick={() => setTab('plan')}>
          <Plan />
          <span>내 플랜{plan.credits > 0 ? ` · ${plan.credits}` : ''}</span>
        </button>
      </nav>

      {open && (
        <CourseDetail
          key={`${open.id}:${school.id}`}
          course={open}
          result={results.get(open.id) ?? { candidates: [] }}
          school={school}
          picked={picked(open)}
          pickState={picks[pickKey(school.id, open.id)]}
          onPick={(id) =>
            setPicks((p) => {
              const next = { ...p };
              const k = pickKey(school.id, open.id);
              if (id === null) delete next[k];
              else next[k] = id;
              return next;
            })
          }
          onUpdate={(patch) => setCourses((prev) => prev.map((c) => (c.id === open.id ? { ...c, ...patch } : c)))}
          onDelete={() => {
            setCourses((prev) => prev.filter((c) => c.id !== open.id));
            setOpenId(null);
          }}
          onClose={closeDetail}
        />
      )}
    </div>
  );
}
