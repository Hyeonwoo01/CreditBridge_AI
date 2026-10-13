import { highlight } from '../lib/text';
import { LIKELIHOOD_LABEL } from '../lib/match';
import type { Likelihood, SubjectArea } from '../lib/types';

export const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

export function Highlighted({ text, keywords }: { text: string; keywords: string[] }) {
  return (
    <>
      {highlight(text, keywords).map((p, i) => (p.mark ? <mark key={i}>{p.text}</mark> : <span key={i}>{p.text}</span>))}
    </>
  );
}

export function LikelihoodBadge({ likelihood }: { likelihood: Likelihood }) {
  return (
    <span className={`badge badge-${likelihood}`}>
      <span className="dot" />
      {LIKELIHOOD_LABEL[likelihood]}
    </span>
  );
}

const AREA_GLYPH: Record<SubjectArea, string> = {
  math: '∫',
  science: 'Δ',
  cs: '</>',
  social: '§',
  humanities: '¶',
};

/** 사진 대신 쓰는 과목 타일 */
export function CourseTile({ code, area, small }: { code: string; area: SubjectArea | null; small?: boolean }) {
  return (
    <div className={`tile tile-${area ?? 'none'}${small ? ' tile-sm' : ''}`} aria-hidden>
      <span className="tile-glyph">{area ? AREA_GLYPH[area] : '?'}</span>
      <span className="tile-code">{code || '—'}</span>
    </div>
  );
}

export function Meter({ value }: { value: number }) {
  return (
    <div className="meter" role="meter" aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={100}>
      <div style={{ width: `${Math.round(value * 100)}%` }} />
    </div>
  );
}
