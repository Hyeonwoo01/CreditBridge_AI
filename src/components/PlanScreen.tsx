import { useState } from 'react';
import type { Plan, RowStatus } from '../lib/plan';
import type { University } from '../lib/types';
import { CourseTile, usd } from './common';
import { Book, Check, Copy } from './Icons';

const STATUS: Record<RowStatus, { label: string; cls: string }> = {
  likely: { label: '인정 예상', cls: 'high' },
  partial: { label: '부분 인정 가능', cls: 'medium' },
  duplicate: { label: '같은 과목과 중복', cls: 'low' },
  grade: { label: '성적 기준 미달', cls: 'low' },
  none: { label: '인정 어려움', cls: 'low' },
};

interface Props {
  plan: Plan;
  school: University;
  tuitionPerCredit: number;
  onTuition: (v: number) => void;
  onOpen: (id: string) => void;
  onGoAnalyze: () => void;
}

/** 어드바이저에게 이메일로 붙여넣을 수 있는 근거 리포트 (영문) */
function reportText(plan: Plan, school: University): string {
  const lines = [
    `Transfer Credit Evidence Report - ${school.name}`,
    `Estimated transferable credit: ${plan.credits} ${school.creditLabel}`,
    '',
  ];
  for (const r of plan.rows) {
    if (!r.match) continue;
    const p = r.course.parsed;
    lines.push(
      `${p.code} ${p.title} (${p.institution || 'Prior institution'}) -> ${r.match.course.code} ${r.match.course.title}: ${Math.round(r.match.score * 100)}% match`,
    );
    for (const u of r.match.units) {
      const ev = u.evidence.slice(0, 2).map((e) => `[${e.where}] ${e.text}`).join(' / ');
      lines.push(`  - ${u.unit.name}: ${Math.round(u.coverage * 100)}%${ev ? ` - ${ev}` : ''}`);
    }
    if (p.textbooks[0]) lines.push(`  - Textbook: ${p.textbooks[0]}`);
    lines.push('');
  }
  lines.push('Generated with CreditBridge. Estimates only; final decisions rest with the receiving institution.');
  return lines.join('\n');
}

export function PlanScreen({ plan, school, tuitionPerCredit, onTuition, onOpen, onGoAnalyze }: Props) {
  const [copied, setCopied] = useState<'idle' | 'done' | 'manual'>('idle');
  if (plan.rows.length === 0) {
    return (
      <div className="screen">
        <div className="empty empty-lg">
          <Book width={32} height={32} />
          <p className="display-sm">아직 분석한 과목이 없어요</p>
          <p className="muted">강의계획서를 올리면 인정 예상 학점과 아낄 수 있는 등록금을 계산해 드려요.</p>
          <button className="btn btn-primary" onClick={onGoAnalyze}>
            과목 분석하러 가기
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="screen">
      <header className="hero">
        <h1 className="display-xl">{school.name} 편입 플랜</h1>
        <p className="muted">중복 수강 없이 졸업까지 아낄 수 있는 시간과 비용이에요.</p>
      </header>

      <div className="plan-layout">
        <section className="summary-card" aria-label="절감 요약">
          <div className="summary-main">
            <span className="rating-display">{plan.credits}</span>
            <span className="title-md">
              {school.creditLabel} 인정 예상
            </span>
          </div>
          <div className="summary-stats">
            <div>
              <span className="display-md">{plan.semestersSaved}학기</span>
              <span className="muted body-sm">단축 가능</span>
            </div>
            <div>
              <span className="display-md">{usd.format(plan.tuitionSaved)}</span>
              <span className="muted body-sm">등록금 절감</span>
            </div>
          </div>
          <label className="text-field">
            <span className="caption muted">학점당 등록금 (USD)</span>
            <input type="number" min={0} step={50} value={tuitionPerCredit} onChange={(e) => onTuition(Math.max(0, Number(e.target.value) || 0))} />
          </label>
          {plan.capped && (
            <p className="body-sm warn-inline">
              {school.name}은 편입생에게 최대 {school.transferCreditCap} {school.creditLabel}까지만 인정해요.
            </p>
          )}
          <button
            className="btn btn-secondary full"
            onClick={() =>
              navigator.clipboard
                .writeText(reportText(plan, school))
                .then(() => setCopied('done'))
                .catch(() => setCopied('manual'))
            }
          >
            {copied === 'done' ? <Check width={18} height={18} /> : <Copy width={18} height={18} />}
            {copied === 'done' ? '리포트를 복사했어요' : '어드바이저용 근거 리포트 복사'}
          </button>
          {copied === 'manual' && (
            <textarea className="report-text" readOnly rows={8} value={reportText(plan, school)} onFocus={(e) => e.target.select()} autoFocus />
          )}
          <p className="caption-sm muted">
            예상치이며 최종 인정 여부는 대학 학사처·학과의 심사로 결정돼요. 등록금은 예시 값이니 실제 금액으로 바꿔 보세요.
          </p>
        </section>

        <section className="plan-rows" aria-label="과목별 인정 현황">
          {plan.rows.map((r) => {
            const s = STATUS[r.status];
            return (
              <button key={r.course.id} className="plan-row" onClick={() => onOpen(r.course.id)}>
                <CourseTile code={r.course.parsed.code} area={r.match?.course.area ?? null} small />
                <div className="plan-row-body">
                  <span className="title-sm ellipsis">{r.course.parsed.title}</span>
                  <span className="body-sm muted ellipsis">
                    {r.match ? `→ ${r.match.course.code} ${r.match.course.title}` : '대체 과목 없음'}
                  </span>
                  <span className={`badge badge-${s.cls}`}>
                    <span className="dot" />
                    {s.label}
                  </span>
                </div>
                <div className="plan-row-credits">
                  <span className="title-md">{r.credits > 0 ? `+${r.credits}` : '0'}</span>
                  <span className="caption-sm muted">{school.creditLabel}</span>
                </div>
              </button>
            );
          })}
        </section>
      </div>

    </div>
  );
}
