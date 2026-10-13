import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { UNIVERSITIES, getUniversity } from './data/catalog';
import { AiUnavailableError, evaluateCourse, extractSyllabus, getAiMode, type AiMode } from './lib/api';
import { candidatesFromEvaluation } from './lib/aiMatch';
import { matchCourse } from './lib/match';
import { buildPlan, pickKey, resolvePick, type Picks } from './lib/plan';
import type { CourseResult, MyCourse } from './lib/types';
import { useStored } from './lib/useStored';
import { AnalyzeScreen } from './components/AnalyzeScreen';
import { CourseDetail } from './components/CourseDetail';
import { PlanScreen } from './components/PlanScreen';
import { Book, Logo, Plan, Sparkle } from './components/Icons';

type Tab = 'analyze' | 'plan';

/** 과목·학교 조합별 AI 분석 상태 */
export type EvalState = { status: 'running' } | { status: 'error'; message: string };

const evalKey = (courseId: string, schoolId: string) => `${courseId}:${schoolId}`;

export default function App() {
  const [courses, setCourses] = useStored<MyCourse[]>('cb.courses', []);
  const [schoolId, setSchoolId] = useStored('cb.school', UNIVERSITIES[0].id);
  const [picks, setPicks] = useStored<Picks>('cb.picks', {});
  const [tuition, setTuition] = useStored<Record<string, number>>('cb.tuition', {});
  const [tab, setTab] = useState<Tab>('analyze');
  const [openId, setOpenId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string[]>([]);
  const [aiMode, setAiMode] = useState<AiMode>(null);
  const [evals, setEvals] = useState<Record<string, EvalState>>({});
  const [queue, setQueue] = useState<{ courseId: string; schoolId: string }[]>([]);
  const running = useRef(false);

  useEffect(() => {
    void getAiMode().then(setAiMode);
  }, []);

  const school = getUniversity(schoolId);
  const tuitionPerCredit = tuition[school.id] ?? school.tuitionPerCredit;

  const results = useMemo(
    () =>
      new Map<string, CourseResult>(
        courses.map((c) => {
          const ev = c.evaluations?.[school.id];
          return [c.id, ev ? { candidates: candidatesFromEvaluation(ev, c, school) } : matchCourse(c, school)];
        }),
      ),
    [courses, school],
  );
  const plan = useMemo(() => buildPlan(courses, results, school, picks, tuitionPerCredit), [courses, results, school, picks, tuitionPerCredit]);

  const enqueue = useCallback((items: { courseId: string; schoolId: string }[]) => {
    if (items.length) setQueue((q) => [...q, ...items.filter((i) => !q.some((x) => x.courseId === i.courseId && x.schoolId === i.schoolId))]);
  }, []);

  // AI 분석은 한 번에 하나씩 실행한다.
  useEffect(() => {
    if (running.current || queue.length === 0) return;
    const [job, ...rest] = queue;
    const course = courses.find((c) => c.id === job.courseId);
    if (!aiMode || !course || course.evaluations?.[job.schoolId]) {
      setQueue(rest);
      return;
    }
    running.current = true;
    const key = evalKey(job.courseId, job.schoolId);
    setEvals((e) => ({ ...e, [key]: { status: 'running' } }));
    evaluateCourse(course, getUniversity(job.schoolId))
      .then((evaluation) => {
        setCourses((prev) =>
          prev.map((c) => (c.id === job.courseId ? { ...c, evaluations: { ...c.evaluations, [job.schoolId]: evaluation } } : c)),
        );
        setEvals(({ [key]: _, ...e }) => e);
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'AI 분석에 실패했어요.';
        setEvals((e) => ({ ...e, [key]: { status: 'error', message } }));
        if (err instanceof AiUnavailableError && err.permanent) {
          setAiMode(null);
          setQueue([]);
        }
      })
      .finally(() => {
        running.current = false;
        setQueue((q) => q.filter((x) => !(x.courseId === job.courseId && x.schoolId === job.schoolId)));
      });
  }, [queue, courses, aiMode, setCourses]);

  const addCourse = useCallback(
    async (text: string, fileName: string) => {
      setBusy((b) => [...b, fileName]);
      try {
        const { parsed, source } = await extractSyllabus(text);
        const course: MyCourse = { id: crypto.randomUUID(), createdAt: Date.now(), fileName, rawText: text, parsed, source, grade: '' };
        setCourses((prev) => [course, ...prev]);
        enqueue([{ courseId: course.id, schoolId }]);
      } finally {
        setBusy((b) => {
          const i = b.indexOf(fileName);
          return i < 0 ? b : [...b.slice(0, i), ...b.slice(i + 1)];
        });
      }
    },
    [setCourses, enqueue, schoolId],
  );

  const changeSchool = (id: string) => {
    setSchoolId(id);
    enqueue(courses.filter((c) => !c.evaluations?.[id]).map((c) => ({ courseId: c.id, schoolId: id })));
  };

  const open = openId ? courses.find((c) => c.id === openId) : undefined;
  const picked = (c: MyCourse) => resolvePick(c, results.get(c.id), school, picks);
  const evalOf = (c: MyCourse) => evals[evalKey(c.id, school.id)];
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
        <span
          className={`ai-status${aiMode ? ' on' : ''}`}
          title={aiMode ? 'Claude가 수업 내용을 비교해요' : '키워드 일치로 추정해요'}
        >
          <Sparkle width={14} height={14} /> {aiMode ? 'AI 내용 분석' : '키워드 분석'}
        </span>
      </header>

      <main>
        {tab === 'analyze' ? (
          <AnalyzeScreen
            school={school}
            schools={UNIVERSITIES}
            onSchool={changeSchool}
            courses={courses}
            results={results}
            picked={picked}
            evalOf={evalOf}
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
          aiAvailable={aiMode !== null}
          evalState={evalOf(open)}
          onEvaluate={() => {
            setEvals(({ [evalKey(open.id, school.id)]: _, ...e }) => e);
            setCourses((prev) =>
              prev.map((c) => {
                if (c.id !== open.id || !c.evaluations?.[school.id]) return c;
                const { [school.id]: _, ...rest } = c.evaluations;
                return { ...c, evaluations: rest };
              }),
            );
            enqueue([{ courseId: open.id, schoolId: school.id }]);
          }}
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
