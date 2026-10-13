import type { SVGProps } from 'react';

type P = SVGProps<SVGSVGElement>;
const base = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' } as const;

export const Logo = (p: P) => (
  <svg width={32} height={32} viewBox="0 0 32 32" aria-hidden {...p}>
    <path d="M3 22h26M6 22v-6M26 22v-6M3 16c5-8 21-8 26 0" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" />
    <path d="M11 22v-7.5M16 22v-9M21 22v-7.5" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" />
  </svg>
);
export const Search = (p: P) => (<svg {...base} {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>);
export const Upload = (p: P) => (<svg {...base} {...p}><path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></svg>);
export const Back = (p: P) => (<svg {...base} {...p}><path d="M15 18 9 12l6-6" /></svg>);
export const Close = (p: P) => (<svg {...base} {...p}><path d="M6 6l12 12M18 6 6 18" /></svg>);
export const Trash = (p: P) => (<svg {...base} {...p}><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" /></svg>);
export const Check = (p: P) => (<svg {...base} {...p}><path d="m5 12 5 5 9-10" /></svg>);
export const Chevron = (p: P) => (<svg {...base} {...p}><path d="m9 6 6 6-6 6" /></svg>);
export const Alert = (p: P) => (<svg {...base} {...p}><path d="M12 3 2 20h20L12 3z" /><path d="M12 10v4M12 17.5v.01" /></svg>);
export const Sparkle = (p: P) => (<svg {...base} {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6" /></svg>);
export const Copy = (p: P) => (<svg {...base} {...p}><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a1 1 0 0 1 1-1h10" /></svg>);
export const Book = (p: P) => (<svg {...base} {...p}><path d="M4 5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2V5z" /><path d="M4 19a2 2 0 0 1 2-2h14" /></svg>);
export const Plan = (p: P) => (<svg {...base} {...p}><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></svg>);
export const Text = (p: P) => (<svg {...base} {...p}><path d="M4 6h16M4 12h16M4 18h10" /></svg>);

export const Laurel = ({ flip, ...p }: P & { flip?: boolean }) => (
  <svg width={28} height={52} viewBox="0 0 28 52" aria-hidden style={flip ? { transform: 'scaleX(-1)' } : undefined} {...p}>
    <g fill="currentColor">
      <path d="M22 50C10 44 4 32 6 16l2 .3C6.4 31 12 42 23 48z" />
      <ellipse cx="6" cy="12" rx="2.6" ry="5.5" transform="rotate(-8 6 12)" />
      <ellipse cx="3.6" cy="22" rx="2.4" ry="5" transform="rotate(-38 3.6 22)" />
      <ellipse cx="5" cy="32" rx="2.4" ry="5" transform="rotate(-52 5 32)" />
      <ellipse cx="9.5" cy="41" rx="2.3" ry="4.8" transform="rotate(-62 9.5 41)" />
      <ellipse cx="12" cy="20" rx="2" ry="4.4" transform="rotate(28 12 20)" />
      <ellipse cx="13" cy="31" rx="2" ry="4.4" transform="rotate(10 13 31)" />
    </g>
  </svg>
);
