import { useEffect, useState } from 'react';
import { evidenceSentence } from '../lib/match';
import type { EvalState } from '../App';
import type { CandidateMatch, CourseResult, MyCourse, University } from '../lib/types';
import { CourseTile, Highlighted, LikelihoodBadge, Meter } from './common';
import { Alert, Back, Check, Laurel, Sparkle, Trash } from './Icons';

const GRADES = ['', 'A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'P'];

interface Props {
  course: MyCourse;
  result: CourseResult;
  school: University;
  picked: CandidateMatch | null;
  pickState: string | undefined;
  aiAvailable: boolean;
  evalState: EvalState | undefined;
  onEvaluate: () => void;
  onPick: (catalogId: string | null) => void;
  onUpdate: (patch: Partial<MyCourse>) => void;
  onDelete: () => void;
  onClose: () => void;
}

export function CourseDetail({ course, result, school, picked, pickState, aiAvailable, evalState, onEvaluate, onPick, onUpdate, onDelete, onClose }: Props) {
  const { candidates } = result;
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [viewId, setViewId] = useState(picked?.course.id ?? candidates[0]?.course.id);
  const view = candidates.find((c) => c.course.id === viewId) ?? candidates[0];
  const p = course.parsed;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    document.body.classList.add('no-scroll');
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.classList.remove('no-scroll');
    };
  }, [onClose]);

  const isPicked = view && picked?.course.id === view.course.id;

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal aria-label={p.title} onClick={(e) => e.stopPropagation()}>
        <div className="sheet-bar">
          <button className="icon-btn" onClick={onClose} aria-label="뒤로">
            <Back />
          </button>
          <span className="title-sm ellipsis">{p.code || '과목 상세'}</span>
          {confirmDelete ? (
            <button className="btn-danger-pill" onClick={onDelete} onBlur={() => setConfirmDelete(false)} autoFocus>
              삭제하기
            </button>
          ) : (
            <button className="icon-btn" onClick={() => setConfirmDelete(true)} aria-label="삭제">
              <Trash />
            </button>
          )}
        </div>

        <div className="sheet-body">
          <div className="detail-head">
            <CourseTile code={p.code} area={view?.course.area ?? null} small />
            <div>
              <p className="muted body-sm">{[p.institution, course.fileName].filter(Boolean).join(' · ')}</p>
              <h2 className="display-lg">{p.title}</h2>
              <div className="detail-meta">
                <label className="inline-field">
                  학점
                  <input
                    type="number"
                    min={0}
                    max={10}
                    step={0.5}
                    value={p.credits ?? ''}
                    placeholder="?"
                    onChange={(e) => onUpdate({ parsed: { ...p, credits: e.target.value === '' ? null : Number(e.target.value) } })}
                  />
                </label>
                <label className="inline-field">
                  성적
                  <select value={course.grade} onChange={(e) => onUpdate({ grade: e.target.value })}>
                    {GRADES.map((g) => (
                      <option key={g} value={g}>
                        {g || '선택'}
                      </option>
                    ))}
                  </select>
                </label>
                <span className="source-tag">
                  {course.source === 'ai' ? (
                    <>
                      <Sparkle width={12} height={12} /> AI 분석
                    </>
                  ) : (
                    '자동 분석'
                  )}
                </span>
              </div>
            </div>
          </div>

          <AiBanner
            method={view?.method ?? (course.evaluations?.[school.id] ? 'ai' : 'keyword')}
            aiAvailable={aiAvailable}
            evalState={evalState}
            onEvaluate={onEvaluate}
          />

          {!view ? (
            <div className="empty">
              <p className="title-md">{school.name}에서 비슷한 과목을 찾지 못했어요</p>
              <p className="muted body-sm">강의계획서에 주차별 주제나 학습 목표가 들어 있는지 확인해 주세요. 다른 대학을 선택해 볼 수도 있어요.</p>
            </div>
          ) : (
            <>
              {candidates.length > 1 && (
                <div className="chips candidate-chips" role="tablist" aria-label="대체 과목 후보">
                  {candidates.map((c) => (
                    <button key={c.course.id} role="tab" aria-selected={c === view} className={`chip${c === view ? ' chip-on' : ''}`} onClick={() => setViewId(c.course.id)}>
                      {c.course.code} · {Math.round(c.score * 100)}%
                    </button>
                  ))}
                </div>
              )}

              <div className="rating">
                <Laurel />
                <div className="rating-center">
                  <span className="rating-display">{Math.round(view.score * 100)}%</span>
                  <LikelihoodBadge likelihood={view.likelihood} />
                </div>
                <Laurel flip />
              </div>
              <p className="rating-caption">
                <strong>
                  {school.name} {view.course.code}
                </strong>{' '}
                {view.course.title} · {view.course.credits} {school.creditLabel}
              </p>
              {view.summary && <p className="ai-summary body-sm">{view.summary}</p>}

              {view.warnings.length > 0 && (
                <ul className="warnings">
                  {view.warnings.map((w) => (
                    <li key={w}>
                      <Alert width={16} height={16} /> {w}
                    </li>
                  ))}
                </ul>
              )}

              <section className="detail-section">
                <h3 className="display-sm">단원별 일치 근거</h3>
                <p className="muted body-sm">
                  {view.method === 'ai'
                    ? '본교 단원의 학습 목표를 실제로 가르쳤는지 비교했어요. 하이라이트는 강의계획서 원문 그대로의 인용이에요.'
                    : '강의계획서에서 찾은 키워드를 하이라이트했어요. 개요에서 언급만 된 내용은 절반까지만 인정해요.'}
                </p>
                {view.units.map((u) => (
                  <div className="unit" key={u.unit.name}>
                    <div className="row-between">
                      <span className="title-sm">
                        {u.unit.nameKo} <span className="muted body-sm">{u.unit.name}</span>
                      </span>
                      <span className="title-sm">{Math.round(u.coverage * 100)}%</span>
                    </div>
                    <Meter value={u.coverage} />
                    {u.reason && <p className="body-sm unit-reason">{u.reason}</p>}
                    {u.evidence.length > 0 ? (
                      <>
                        {view.method === 'keyword' && <p className="evidence-summary body-sm">{evidenceSentence(course, u, view.course)}</p>}
                        <ul className="evidence">
                          {u.evidence.map((e, i) => (
                            <li key={i}>
                              <span className="evidence-where">{e.where}</span>
                              <span>
                                {e.quote ? <mark>{e.text}</mark> : <Highlighted text={e.text} keywords={e.matchedKeywords} />}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </>
                    ) : (
                      !u.reason && <p className="muted body-sm">관련 내용을 찾지 못했어요.</p>
                    )}
                  </div>
                ))}
                {view.textbookMatch && (
                  <p className="body-sm textbook-note">
                    <Check width={14} height={14} /> 교재 일치: {view.textbookMatch}
                  </p>
                )}
              </section>
            </>
          )}

          <details className="detail-section extracted">
            <summary className="display-sm">추출된 강의계획서 정보</summary>
            <dl>
              {p.description && (
                <>
                  <dt>강의 개요</dt>
                  <dd>{p.description}</dd>
                </>
              )}
              {p.outcomes.length > 0 && (
                <>
                  <dt>학습 목표</dt>
                  <dd>
                    <ul>{p.outcomes.map((o) => <li key={o}>{o}</li>)}</ul>
                  </dd>
                </>
              )}
              {p.weeks.length > 0 && (
                <>
                  <dt>주차별 주제</dt>
                  <dd>
                    <ul>
                      {p.weeks.map((w, i) => (
                        <li key={i}>
                          <span className="muted">{w.label}</span> {w.topic}
                        </li>
                      ))}
                    </ul>
                  </dd>
                </>
              )}
              {p.textbooks.length > 0 && (
                <>
                  <dt>교재</dt>
                  <dd>{p.textbooks.join(' / ')}</dd>
                </>
              )}
              {p.prerequisites.length > 0 && (
                <>
                  <dt>선수 과목</dt>
                  <dd>{p.prerequisites.join(' / ')}</dd>
                </>
              )}
              {p.assessments.length > 0 && (
                <>
                  <dt>평가 방식</dt>
                  <dd>{p.assessments.join(' · ')}</dd>
                </>
              )}
            </dl>
          </details>
        </div>

        {view && (
          <div className="sheet-footer">
            <button className="btn btn-text" onClick={() => onPick(pickState === 'none' ? null : 'none')}>
              {pickState === 'none' ? '플랜에 다시 포함' : '플랜에서 제외'}
            </button>
            <button className={`btn ${isPicked ? 'btn-secondary' : 'btn-primary'}`} onClick={() => onPick(view.course.id)} disabled={isPicked}>
              {isPicked ? (
                <>
                  <Check width={18} height={18} /> 플랜에 담김
                </>
              ) : (
                `${view.course.code}로 플랜에 담기`
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function AiBanner({
  method,
  aiAvailable,
  evalState,
  onEvaluate,
}: {
  method: 'ai' | 'keyword';
  aiAvailable: boolean;
  evalState: EvalState | undefined;
  onEvaluate: () => void;
}) {
  if (evalState?.status === 'running') {
    return (
      <div className="ai-banner">
        <span className="spinner" />
        <span className="body-sm">AI가 강의계획서와 본교 단원별 학습 목표를 비교하고 있어요. 30초~1분 정도 걸려요.</span>
      </div>
    );
  }
  if (method === 'ai') {
    return (
      <div className="ai-banner ai-banner-on">
        <Sparkle width={16} height={16} />
        <span className="body-sm">
          <strong>AI 내용 분석</strong> · 단어가 아니라 실제로 가르친 내용과 깊이, 과목 수준을 비교했어요.
        </span>
        {aiAvailable && (
          <button className="btn-link body-sm" onClick={onEvaluate}>
            다시 분석
          </button>
        )}
      </div>
    );
  }
  return (
    <div className="ai-banner">
      <span className="body-sm">
        <strong>키워드 추정</strong> · {evalState?.status === 'error' ? evalState.message : '같은 단어가 나오는지로 추정한 결과예요.'}
      </span>
      {aiAvailable && (
        <button className="btn-link body-sm" onClick={onEvaluate}>
          AI로 내용 비교하기
        </button>
      )}
    </div>
  );
}
