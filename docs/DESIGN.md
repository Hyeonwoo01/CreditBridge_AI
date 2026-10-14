---
version: 1.1.0
name: CreditBridge-AI-Apple-Base-Design
description: Apple의 절제된 갤러리형 UI 미학(여백 중심의 레이아웃, 1px 헤어라인, 단일 Action Blue #0066cc 인터랙티브 컬러, 정교한 SF Pro/Pretendard 타이포그래피)을 대학 편입 학점 심사 자동화 SaaS인 CreditBridge_AI에 맞게 재해석한 디자인 시스템. 장식적 크롬과 불필요한 그림자를 배제하여 '강의계획서 원문 근거(Evidence)'와 '개념 커버리지 데이터'가 주인공이 되도록 설계되었으며, 인간 중심 의사결정(Human-in-the-Loop) 원칙에 따라 학과 교수·심사관·편입생·기관 관리자의 가독성과 판단 정확도를 극대화한다.

colors:
  primary: "#0066cc"
  primary-focus: "#0071e3"
  primary-on-dark: "#2997ff"
  ink: "#1d1d1f"
  body: "#1d1d1f"
  body-on-dark: "#ffffff"
  body-muted: "#cccccc"
  ink-muted-80: "#333333"
  ink-muted-48: "#7a7a7a"
  divider-soft: "#f0f0f0"
  hairline: "#e0e0e0"
  canvas: "#ffffff"
  canvas-parchment: "#f5f5f7"
  surface-pearl: "#fafafc"
  surface-tile-1: "#272729"
  surface-tile-2: "#2a2a2c"
  surface-tile-3: "#252527"
  surface-black: "#000000"
  surface-chip-translucent: "#d2d2d7"
  on-primary: "#ffffff"
  on-dark: "#ffffff"
  status-approve: "#1d8348"
  surface-approve-subtle: "#e8f8f0"
  status-elective: "#b76e00"
  surface-elective-subtle: "#fef5e7"
  status-reject: "#c9342b"
  surface-reject-subtle: "#fdecea"
  highlight-evidence-source: "#fff8c5"
  highlight-evidence-target: "#e6f2ff"

typography:
  hero-display:
    fontFamily: "SF Pro Display, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 56px
    fontWeight: 600
    lineHeight: 1.07
    letterSpacing: -0.28px
  display-lg:
    fontFamily: "SF Pro Display, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 40px
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: 0
  display-md:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 34px
    fontWeight: 600
    lineHeight: 1.47
    letterSpacing: -0.374px
  lead:
    fontFamily: "SF Pro Display, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 28px
    fontWeight: 400
    lineHeight: 1.14
    letterSpacing: 0.196px
  lead-airy:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 24px
    fontWeight: 300
    lineHeight: 1.5
    letterSpacing: 0
  tagline:
    fontFamily: "SF Pro Display, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 21px
    fontWeight: 600
    lineHeight: 1.19
    letterSpacing: 0.231px
  body-strong:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 17px
    fontWeight: 600
    lineHeight: 1.24
    letterSpacing: -0.374px
  body:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 17px
    fontWeight: 400
    lineHeight: 1.47
    letterSpacing: -0.374px
  dense-link:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 17px
    fontWeight: 400
    lineHeight: 2.41
    letterSpacing: 0
  caption:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.43
    letterSpacing: -0.224px
  caption-strong:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 14px
    fontWeight: 600
    lineHeight: 1.29
    letterSpacing: -0.224px
  button-large:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 18px
    fontWeight: 300
    lineHeight: 1.0
    letterSpacing: 0
  button-utility:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.29
    letterSpacing: -0.224px
  fine-print:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.0
    letterSpacing: -0.12px
  micro-legal:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 10px
    fontWeight: 400
    lineHeight: 1.3
    letterSpacing: -0.08px
  nav-link:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.0
    letterSpacing: -0.12px
  mono-code:
    fontFamily: "SF Mono, JetBrains Mono, ui-monospace, SFMono-Regular, monospace"
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.4
    letterSpacing: 0
  eyebrow:
    fontFamily: "SF Pro Text, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.0
    letterSpacing: 0.08em
    textTransform: uppercase
  kpi-number:
    fontFamily: "SF Pro Display, Pretendard Variable, Pretendard, system-ui, -apple-system, sans-serif"
    fontSize: 40px
    fontWeight: 600
    lineHeight: 1.0
    letterSpacing: 0

rounded:
  none: 0px
  xs: 5px
  sm: 8px
  md: 11px
  lg: 18px
  pill: 9999px
  full: 9999px

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 17px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 80px

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    padding: 11px 22px
  button-primary-focus:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.pill}"
  button-primary-active:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.pill}"
  button-secondary-pill:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.primary}"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    padding: 11px 22px
  button-dark-utility:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.on-dark}"
    typography: "{typography.button-utility}"
    rounded: "{rounded.sm}"
    padding: 8px 15px
  button-pearl-capsule:
    backgroundColor: "{colors.surface-pearl}"
    textColor: "{colors.ink-muted-80}"
    typography: "{typography.caption}"
    rounded: "{rounded.md}"
    padding: 8px 14px
  button-simulation-hero:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button-large}"
    rounded: "{rounded.pill}"
    padding: 14px 28px
  button-icon-circular:
    backgroundColor: "{colors.surface-chip-translucent}"
    textColor: "{colors.ink}"
    rounded: "{rounded.full}"
    size: 44px
  text-link:
    backgroundColor: transparent
    textColor: "{colors.primary}"
    typography: "{typography.body}"
  text-link-on-dark:
    backgroundColor: transparent
    textColor: "{colors.primary-on-dark}"
    typography: "{typography.body}"
  global-nav:
    backgroundColor: "{colors.surface-black}"
    textColor: "{colors.on-dark}"
    typography: "{typography.nav-link}"
    height: 44px
  sub-nav-frosted:
    backgroundColor: "{colors.canvas-parchment}"
    textColor: "{colors.ink}"
    typography: "{typography.tagline}"
    height: 52px
  summary-tile-light:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.display-lg}"
    rounded: "{rounded.none}"
    padding: 80px
  summary-tile-parchment:
    backgroundColor: "{colors.canvas-parchment}"
    textColor: "{colors.ink}"
    typography: "{typography.display-lg}"
    rounded: "{rounded.none}"
    padding: 80px
  summary-tile-dark:
    backgroundColor: "{colors.surface-tile-1}"
    textColor: "{colors.on-dark}"
    typography: "{typography.display-lg}"
    rounded: "{rounded.none}"
    padding: 80px
  summary-tile-dark-2:
    backgroundColor: "{colors.surface-tile-2}"
    textColor: "{colors.on-dark}"
    rounded: "{rounded.none}"
  summary-tile-dark-3:
    backgroundColor: "{colors.surface-tile-3}"
    textColor: "{colors.on-dark}"
    rounded: "{rounded.none}"
  evaluation-utility-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.lg}"
    padding: 24px
  syllabus-split-pane:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: 24px
  evidence-quote-block:
    backgroundColor: "{colors.canvas-parchment}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: 17px 24px
  decision-option-chip:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: 12px 16px
  decision-option-chip-selected:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
  confidence-badge-pill:
    backgroundColor: "{colors.surface-pearl}"
    textColor: "{colors.ink-muted-80}"
    typography: "{typography.caption-strong}"
    rounded: "{rounded.pill}"
    padding: 4px 12px
  upload-dropzone-card:
    backgroundColor: "{colors.canvas-parchment}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: 48px
  search-input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    padding: 12px 20px
    height: 44px
  floating-sticky-bar:
    backgroundColor: "{colors.canvas-parchment}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    height: 64px
    padding: 12px 32px
  footer:
    backgroundColor: "{colors.canvas-parchment}"
    textColor: "{colors.ink-muted-80}"
    typography: "{typography.fine-print}"
    padding: 32px
  workspace-sub-bar:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.caption}"
    height: 44px
  count-chip:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink-muted-80}"
    typography: "{typography.fine-print}"
    rounded: "{rounded.pill}"
    padding: 3px 10px
  count-chip-approve:
    backgroundColor: "{colors.surface-approve-subtle}"
    textColor: "{colors.status-approve}"
    rounded: "{rounded.pill}"
  filter-chip:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink-muted-80}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    height: 36px
  filter-chip-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.on-dark}"
    rounded: "{rounded.pill}"
  page-header-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.display-md}"
    rounded: "{rounded.lg}"
    padding: 24px
  summary-hero-card-dark:
    backgroundColor: "{colors.surface-tile-1}"
    textColor: "{colors.on-dark}"
    typography: "{typography.display-lg}"
    rounded: "{rounded.lg}"
    padding: 48px
  metric-card-on-dark:
    backgroundColor: "rgba(255, 255, 255, 0.06)"
    textColor: "{colors.on-dark}"
    rounded: "{rounded.md}"
    padding: 20px
  kpi-card:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.kpi-number}"
    rounded: "{rounded.lg}"
    padding: 20px
  stat-tile:
    backgroundColor: "{colors.canvas-parchment}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 16px
  coverage-ring:
    size: 22px
    stroke: 3px
    trackColor: "{colors.hairline}"
  data-table:
    backgroundColor: "{colors.canvas}"
    headerBackground: "{colors.surface-pearl}"
    rounded: "{rounded.lg}"
  avatar-initial:
    backgroundColor: "{colors.highlight-evidence-target}"
    textColor: "{colors.primary}"
    rounded: "{rounded.full}"
    size: 28px
  selection-bar-dark:
    backgroundColor: "{colors.surface-tile-1}"
    textColor: "{colors.on-dark}"
    rounded: "{rounded.lg}"
    padding: 12px 20px
  progress-stepper:
    activeColor: "{colors.primary}"
    trackColor: "{colors.hairline}"
    size: 24px
  reason-dialog:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    width: 640px
    backdrop: "rgba(0, 0, 0, 0.5)"
  reason-option-row:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.md}"
    padding: 12px 16px
  reason-option-row-selected:
    backgroundColor: "{colors.surface-reject-subtle}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
---

## Overview

**CreditBridge_AI**의 디자인 시스템은 Apple의 핵심 철학인 **'거의 보이지 않는 UI 프레임 속에 핵심 대상을 미술관 작품처럼 부각하는 절제미'**를 대학 편입 학점 심사 자동화 SaaS에 맞게 계승·발전시킨 설계 기준서입니다. Apple 스토어에서 제품 사진이 주인공이라면, CreditBridge_AI에서는 **강의계획서 원문 인용 근거(Evidence Quote)**와 **교과목 개념 커버리지 데이터(Concept Coverage %)**가 주인공입니다. 장식적인 그라데이션, 불필요한 카드 그림자, 과도한 테두리를 모두 걷어내어 학과 교수, 심사관, 편입생, 기관 관리자가 오직 텍스트 근거와 수치 데이터에만 집중할 수 있도록 돕습니다.

특히 본 서비스의 핵심 원칙인 **Human-in-the-Loop (AI는 근거를 제시하는 보조자이며, 최종 학점 인정 결정권은 전적으로 학과 교수에게 있음)**를 시각적 위계로 구현합니다. 모든 클릭 가능한 인터랙티브 액션(판정 확정, 보완 요청, SIS 내보내기, 시뮬레이션 실행)은 오직 단일 브랜드 컬러인 **Action Blue (`#0066cc`)**로만 표현되며, AI 신뢰도(High/Medium/Low)나 3단계 추천 등급(학점 인정/일반선택/불인정), 과거 판정 불일치 경고는 버튼이 아닌 **읽기 전용 시맨틱 배지와 원문 하이라이트**로만 제한적으로 작동합니다.

랜딩 및 학생 사전 시뮬레이션 화면(F-09)은 Apple 특유의 라이트/다크 풀블리드 타일 교차 리듬을 활용하여 예상 인정 학점, 잔여 학기, 예상 추가 비용을 직관적인 대형 타이포그래피로 전달합니다. 반면 심사관 큐(F-07)와 교수용 원문 대조 심사 화면(F-04)은 Apple 스토어 컨피규레이터의 정교한 유틸리티 그리드(`{rounded.lg}` 18px 라운드 + `1px` 헤어라인 보더)와 기관·업무 맥락을 보여주는 흰색 보조 바(`{component.workspace-sub-bar}`), 하단 고정 판정 바(`{component.floating-sticky-bar}`)를 결합해 고밀도 심사 업무에서도 시각적 피로도를 최소화합니다.

> **v1.1.0 변경 (화면 목업 반영):** 심사 큐, 학생 시뮬레이션 리포트, 관리자 콘솔, 불인정 사유 선택 창을 목업에 맞춰 개편하면서 아래 컴포넌트가 추가·변경되었습니다. 풀블리드 다크 타일 → 라운드 카드형 다크 히어로(`{component.summary-hero-card-dark}`), 프로스티드 서브 내비 → 흰색 기관 보조 바(`{component.workspace-sub-bar}`) + 집계 칩(`{component.count-chip}`), 필터 칩 선택 상태 → 잉크 채움(`{component.filter-chip-selected}`), 커버리지 원형 게이지(`{component.coverage-ring}`), 진행 단계(`{component.progress-stepper}`), 하단 다크 선택 바(`{component.selection-bar-dark}`), 사유 선택 모달(`{component.reason-dialog}`). 최대 폭은 기본 `1280px`, 심사 큐와 원문 대조 화면만 `1440px`로 정했습니다.

**Key Characteristics:**
- **근거 중심(Evidence-First) 프레젠테이션:** UI 크롬이 뒤로 물러나고 강의계획서(Syllabus) 원문 인용구와 본교 과목 편람(Catalog) 대조 뷰가 화면의 중심을 차지함.
- **단일 인터랙티브 액센트 (`{colors.primary}` — #0066cc):** 모든 버튼, 링크, 포커스 링, 선택 칩은 오직 Action Blue 하나만 사용하여 사용자의 행동 지점을 명확히 안내함.
- **비간섭 시맨틱 상태 토큰:** AI 신뢰도(High/Medium/Low), 3단계 판정 상태, 원문 인용 하이라이트(F-04), 과거 판정 충돌 경고(F-08)는 저채도 파스텔 배경과 고대비 텍스트 배지로만 표시하여 Action Blue와 시각적으로 충돌하지 않음.
- **두 가지 버튼 문법:** 핵심 의사결정용 캡슐형 필 버튼(`{rounded.pill}`)과 글로벌/보조 유틸리티용 컴팩트 버튼(`{rounded.sm}`, `{rounded.md}`).
- **한·영 혼용 학술 텍스트에 최적화된 타이포그래피:** `SF Pro Display / SF Pro Text`와 `Pretendard Variable`을 결합하고, 본문 크기를 16px이 아닌 **17px (행간 1.47)**로 설정하여 국·영문 강의계획서 장기 열람 시 독서와 같은 편안한 호흡을 제공함.
- **절제된 깊이감(Whisper-soft Elevation):** 일반 UI 카드나 버튼에는 그림자를 전혀 쓰지 않으며, 오직 캔버스 위에 띄워진 **원본 강의계획서 PDF 프리뷰 모달/시트**에만 단일 드롭 섀도우(`rgba(0, 0, 0, 0.22) 3px 5px 30px`)를 부여함. 사유 선택 창 같은 UI 모달은 그림자 대신 `rgba(0, 0, 0, 0.5)` 배경 딤(backdrop)으로 분리함.
- **2단 내비게이션 + 하단 플로팅 바:** 슬림한 블랙 `{component.global-nav}`(44px, 고정) + 심사관·교수·관리자용 흰색 `{component.workspace-sub-bar}`(기관명 · 업무 위치 · 제출 요청/심사 대기/판정 완료 집계 칩) + 교수 심사용 하단 `{component.floating-sticky-bar}`(64px) 또는 심사 큐 일괄 처리용 `{component.selection-bar-dark}`로 스크롤 중에도 컨텍스트와 즉시 액션을 유지함.

## Colors

> **적용 대상 화면 (4대 페르소나 워크스페이스):** (1) 편입생 입학 전 시뮬레이션 및 진행 현황 포털(이지원), (2) 심사관 대기열 큐 및 교수 배정/SIS 연동 대시보드(레이첼), (3) 학과 교수 좌우 원문 대조 심사 화면, (4) 기관 관리자 통계·문서보존·감사로그 콘솔. 모든 화면은 동일한 컬러 토큰 체계를 공유하며 표면(Surface) 배합 비율로만 모드를 전환합니다.

### Brand & Accent
- **Action Blue** (`{colors.primary}` — `#0066cc`): 시스템 전체에서 유일한 인터랙티브 브랜드 컬러입니다. 모든 텍스트 링크, 주요 캡슐형 CTA 버튼("판정 확정", "학점 시뮬레이션 시작", "SIS로 내보내기", "보완 서류 제출"), 그리고 포커스 링의 기준색으로 사용됩니다. 클릭 시 색상 변경 대신 `transform: scale(0.95)` 미세 축소 트랜지션으로 물리적 피드백을 전달합니다.
- **Focus Blue** (`{colors.primary-focus}` — `#0071e3`): 키보드 접근성 포커스 링(`outline: 2px solid`) 및 선택된 판정 옵션 칩(`{component.decision-option-chip-selected}`)의 2px 강조 테두리에 사용되는 한 톤 밝은 블루입니다.
- **Sky Link Blue** (`{colors.primary-on-dark}` — `#2997ff`): 다크 요약 타일(`{colors.surface-tile-1}`)이나 상단 블랙 내비게이션 위에서 텍스트 링크 및 핵심 수치 강조에 사용되는 고명도 블루입니다.

### Surface
- **Pure White** (`{colors.canvas}` — `#ffffff`): 기본 작업 캔버스이자 모든 유틸리티 카드(`{component.evaluation-utility-card}`), 좌우 원문 대조 패널(`{component.syllabus-split-pane}`), 테이블 행의 배경색입니다.
- **Parchment** (`{colors.canvas-parchment}` — `#f5f5f7`): Apple 특유의 오프화이트 배경입니다. 대시보드의 기본 바탕색으로 사용되어, 그 위에 올라가는 Pure White(`#ffffff`) 심사 카드들이 그림자 없이도 명확한 영역감을 갖게 합니다. 또한 원문 인용 블록(`{component.evidence-quote-block}`), PDF 업로드 드롭존(`{component.upload-dropzone-card}`), 푸터 영역의 배경으로 쓰입니다.
- **Pearl Button** (`{colors.surface-pearl}` — `#fafafc`): Parchment(`#f5f5f7`)보다 미세하게 밝은 톤으로, 보조 캡슐 버튼("이력 보기", "임시 저장", "대리 심사자 지정")이나 중립 상태 배지의 배경으로 사용됩니다.
- **Near-Black Tile 1** (`{colors.surface-tile-1}` — `#272729`): 학생 시뮬레이션 리포트의 다크 히어로 카드(`{component.summary-hero-card-dark}`: 예상 인정 학점·남은 학기·추가 비용·심사 진행)와 심사 큐 하단 선택 바(`{component.selection-bar-dark}`)의 배경입니다.
- **Near-Black Tile 2** (`{colors.surface-tile-2}` — `#2a2a2c`): 다크 타일 내부에서 세부 메트릭 카드를 한 단계 분리할 때 사용하는 미세 명도 차 표면입니다. 구현에서는 같은 효과를 `rgba(255, 255, 255, 0.06)` 오버레이(`{component.metric-card-on-dark}`)로 냅니다.
- **Near-Black Tile 3** (`{colors.surface-tile-3}` — `#252527`): 다크 섹션 하단이나 OCR 원문 스캔 이미지 뷰어 프레임에 사용됩니다.
- **Pure Black** (`{colors.surface-black}` — `#000000`): 최상단 글로벌 내비게이션 바(`{component.global-nav}`)와 전체화면 PDF 원본 비교 모달의 배경, 그리고 50% 투명도로 UI 모달 배경 딤에만 제한적으로 사용됩니다.
- **Translucent Chip Gray** (`{colors.surface-chip-translucent}` — `#d2d2d7`): 원문 뷰어 확대/축소, 모달 닫기, 페이지 넘김 등 원형 컨트롤 버튼(`{component.button-icon-circular}`)에 `rgba(210, 210, 215, 0.64)` 형태로 적용됩니다.

### Text
- **Near-Black Ink** (`{colors.ink}` — `#1d1d1f`): 모든 헤드라인, 과목명, 본문 텍스트, 다크 유틸리티 버튼의 기본 색상입니다. 순수 검정(`#000000`) 대신 사용하여 장시간 강의계획서를 읽는 교수와 심사관의 눈부심을 방지합니다.
- **Body** (`{colors.body}` — `#1d1d1f`): 라이트 표면 위의 모든 기본 본문 텍스트 색상입니다.
- **Body On Dark** (`{colors.body-on-dark}` — `#ffffff`): 다크 타일 및 글로벌 내비게이션 바 위의 기본 텍스트 색상입니다.
- **Body Muted** (`{colors.body-muted}` — `#cccccc`): 다크 타일 내부의 보조 설명 레이블(예: "기준 학년도 2026", "평균 심사 소요 시간")에 사용됩니다.
- **Ink Muted 80** (`{colors.ink-muted-80}` — `#333333`): Pearl 캡슐 버튼 내부 텍스트, 테이블 보조 열, 푸터 링크에 사용됩니다.
- **Ink Muted 48** (`{colors.ink-muted-48}` — `#7a7a7a`): 비활성화된 버튼, 타임스탬프, 문서 보존 기한 안내, 법적 고지 문구(AI 보조 심사 면책 조항 등)에 사용됩니다.

### Semantic Status, AI Confidence & Evidence Highlights (CreditBridge_AI 전용)
> **원칙:** 시맨틱 컬러는 오직 **상태 배지(Badge), 개념 커버리지 게이지 바, 원문 대조 하이라이트**에만 사용하며, 절대 버튼 배경색으로 사용하지 않습니다.

- **Approve / High Confidence** (`{colors.status-approve}` `#1d8348` 텍스트 · `{colors.surface-approve-subtle}` `#e8f8f0` 배경): `학점 인정(Direct Transfer)` 판정, 학생 화면의 `승인 완료` 라벨, `AI 신뢰도 높음(High)`, 개념 커버리지 75% 이상(`scoring.DIRECT_MIN`) 수치, 집계 칩 `판정 완료`.
- **Elective / Medium Confidence / Supplement Needed** (`{colors.status-elective}` `#b76e00` 텍스트 · `{colors.surface-elective-subtle}` `#fef5e7` 배경): `일반선택 인정(Elective Credit)` 판정, `AI 신뢰도 보통(Medium)`, 커버리지 40~74%, 정보 부족 진단 및 보완 서류 요청(F-06) 상태, 교수 화면에서 확정 전에 확인을 받는 일관성 콜아웃(과거 판정 이력 카드·사유 선택 창 안의 경보).
- **Reject / Low Confidence / Consistency Alert** (`{colors.status-reject}` `#c9342b` 텍스트 · `{colors.surface-reject-subtle}` `#fdecea` 배경): `학점 불인정(Rejection)` 판정, `AI 신뢰도 낮음(Low)`, 커버리지 40% 미만, 과거 유사 강의계획서(유사도 ≥80%) 판정 이력과 상충될 때 심사 큐에 표시하는 **일관성 경보 인라인 행(F-08)** 과 `과거 판정 확인 필요` 배지, 선택된 불인정 사유 행(`{component.reason-option-row-selected}`), 폼 유효성 에러.
- **Evidence Quote Highlights (F-04 원문 근거 하이라이트):**
  - `{colors.highlight-evidence-source}` (`#fff8c5` 소프트 앰버 옐로우): 제출된 타교 강의계획서(Syllabus) 원문에서 추출된 매칭 근거 문장 하이라이트 배경.
  - `{colors.highlight-evidence-target}` (`#e6f2ff` 소프트 아이스 블루): 본교 학과 과목 편람(Target Catalog)에서 대응되는 학습 목표/주차별 주제 하이라이트 배경.

### Hairlines & Borders
- **Divider Soft** (`{colors.divider-soft}` — `#f0f0f0`): 보조 버튼의 소프트 링 보더 및 강의계획서 주차별(Week 1~16) 목록 사이의 미세 구분선(`rgba(0, 0, 0, 0.04)`).
- **Hairline** (`{colors.hairline}` — `#e0e0e0`): 심사 유틸리티 카드, 좌우 원문 대조 패널, 판정 선택 칩의 기본 `1px solid` 테두리입니다.

### Brand Gradient
**장식용 CSS 그라데이션을 일체 사용하지 않습니다.** 시각적 리듬과 깊이감은 오직 표면 색상 교차(`#ffffff` ↔ `#f5f5f7` ↔ `#272729`), 정교한 1px 헤어라인, 그리고 스티키 바의 프로스티드 글래스 블러(`backdrop-filter: saturate(180%) blur(20px)`)로만 구현합니다. 단, 커버리지 원형 게이지(`{component.coverage-ring}`)의 `conic-gradient`는 수치를 그리는 데이터 표현이라 예외로 허용합니다.

## Typography

### Font Family
- **Display**: `"SF Pro Display", "Pretendard Variable", Pretendard, system-ui, -apple-system, sans-serif` — 19px 이상의 대형 타이틀, 입학 전 시뮬레이션 결과 수치(인정 학점, 잔여 학기, 예상 등록금), 과목 매칭 헤드라인에 사용됩니다.
- **Body / UI**: `"SF Pro Text", "Pretendard Variable", Pretendard, system-ui, -apple-system, sans-serif` — 국·영문 강의계획서 원문(F-01/F-02), 인용구 대조(F-04), 심사 큐 테이블, 버튼 및 캡션 등 20px 미만의 모든 텍스트에 사용됩니다.
- **Monospace (`{typography.mono-code}`)**: `"SF Mono", "JetBrains Mono", ui-monospace, SFMono-Regular, monospace` — 학수번호(`CSE-3021`), SIS 연동 API 토큰, 감사 로그 해시, OCR 신뢰도 수치 표기에 사용됩니다.
- **OpenType features**: 학점 합계, 개념 커버리지(%), 유사도(%), 학비 시뮬레이션 표 등 모든 숫자 영역에 `font-variant-numeric: tabular-nums`를 강제 적용하여 행간 숫자 정렬이 흔들리지 않도록 합니다.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use in CreditBridge_AI |
|---|---|---|---|---|---|
| `{typography.hero-display}` | 56px | 600 | 1.07 | -0.28px | 랜딩 히어로 및 학생 사전 시뮬레이션 핵심 수치(예: "최대 68학점 인정 예상") |
| `{typography.display-lg}` | 40px | 600 | 1.10 | 0 | 대시보드 요약 타일 헤드라인, 학과별 심사 현황 메인 타이틀 |
| `{typography.display-md}` | 34px | 600 | 1.47 | -0.374px | 주요 섹션 타이틀 (예: "원문 근거 대조", "과거 유사 판정 이력") |
| `{typography.lead}` | 28px | 400 | 1.14 | 0.196px | 시뮬레이션 서브카피 및 과목 매칭 요약 리드 문구 |
| `{typography.lead-airy}` | 24px | 300 | 1.5 | 0 | 학생 진행 현황 포털(F-10) 단계별 안내 문구 (Weight 300 적용) |
| `{typography.tagline}` | 21px | 600 | 1.19 | 0.231px | 서브 내비게이션 워크스페이스 제목, 좌우 대조 패널의 과목명 타이틀 |
| `{typography.body-strong}` | 17px | 600 | 1.24 | -0.374px | 카드 내 강조 제목, 인용문 핵심 키워드, 심사 큐의 학생/과목명 |
| `{typography.body}` | 17px | 400 | 1.47 | -0.374px | 기본 본문, 강의계획서 학습목표·주차별 강의내용 원문, 주요 버튼 텍스트 |
| `{typography.dense-link}` | 17px | 400 | 2.41 | 0 | 푸터 링크 컬럼, 학과 편람 카테고리 리스트 (여유로운 행간) |
| `{typography.caption}` | 14px | 400 | 1.43 | -0.224px | 보조 설명, 판정 옵션 칩 레이블, 보완 서류 가이드 세부 항목 |
| `{typography.caption-strong}` | 14px | 600 | 1.29 | -0.224px | 테이블 헤더(TH), 시맨틱 신뢰도 배지, 커버리지(%) 수치 라벨 |
| `{typography.button-large}` | 18px | 300 | 1.0 | 0 | 학생 사전 시뮬레이션 시작 히어로 CTA 버튼 (Weight 300) |
| `{typography.button-utility}` | 14px | 400 | 1.29 | -0.224px | 서브 내비게이션 필터 링크, 다크 유틸리티 버튼("CSV 내보내기", "로그아웃") |
| `{typography.fine-print}` | 12px | 400 | 1.0 | -0.12px | 푸터 본문, AI 추천 보조 안내문, 파일 업로드 규격 안내 |
| `{typography.micro-legal}` | 10px | 400 | 1.3 | -0.08px | Human-in-the-Loop 법적 책임 고지, 개인정보 및 문서 보존/파기 정책 캡션 |
| `{typography.nav-link}` | 12px | 400 | 1.0 | -0.12px | 최상단 글로벌 내비게이션(`global-nav`) 메뉴 항목 |
| `{typography.mono-code}` | 13px | 400 | 1.40 | 0 | 학수번호, SIS API 엔드포인트(`GET /api/sis/decisions`), 감사로그 ID(`LOG-000123`), 접수 번호(`#2-6`) |
| `{typography.eyebrow}` | 12px | 600 | 1.0 | 0.08em (대문자) | 페이지 제목 위 맥락 라벨(`GOVERNANCE`, `TRANSFER CREDIT SIMULATION`), `{colors.primary}` 색 |
| `{typography.kpi-number}` | 40px | 600 | 1.0 | 0 | 관리자 콘솔·심사 큐 KPI 카드의 핵심 수치(AI 추천 수용률 등), 단위는 17px muted로 뒤에 붙임 |

### Principles

- **디스플레이 및 본문 사이즈의 네거티브 자간(Negative Letter-Spacing):** 17px 이상의 모든 타이틀과 본문에 `-0.12px ~ -0.374px`의 미세한 자간 축소를 적용하여 Apple 특유의 단단하고 정돈된 타이포그래피 밀도를 구현합니다. 12px 이하 캡션에는 가독성을 위해 과도한 자간 축소를 피합니다.
- **16px이 아닌 17px 본문 기준:** 일반 B2B SaaS의 14~16px 관행을 깨고 강의계획서 원문 및 설명 본문을 **17px (`line-height: 1.47`)**로 설정합니다. 학과 교수가 수십 페이지 분량의 국·영문 강의계획서와 편람을 대조할 때 ‘스캔’이 아닌 ‘정독’이 가능하도록 눈의 피로를 줄여줍니다.
- **Weight 500 배제 (300 / 400 / 600 / 700 체계):** 어중간한 500(Medium) 굵기를 쓰지 않고 본문은 `400`, 강조 본문과 헤드라인은 `600`으로 대비를 명확히 합니다. `300`(Light)은 시뮬레이션 대형 버튼(`{typography.button-large}`)과 포털 리드 문구(`{typography.lead-airy}`)에만 제한적으로 사용하여 여유로운 인상을 줍니다.

### Note on Font Substitutes & Multilingual Support
CreditBridge_AI는 한국어와 영어 강의계획서를 별도 번역 없이 동시에 처리(F-01)하므로 한·영 자폭 및 베이스라인 조화가 중요합니다:

- macOS/iOS 환경에서는 `SF Pro Display / SF Pro Text`가 영문을, 시스템 산돌고딕네오 또는 프리텐다드가 국문을 렌더링합니다.
- Windows/Linux를 포함한 크로스 플랫폼 일관성을 위해 웹폰트로 **`Pretendard Variable`**(또는 영문 보조 `Inter`)을 최우선 폴백으로 로드합니다.
- `Pretendard Variable` 적용 시 본문 행간은 `1.47`(한글 다단 문단에서는 필요 시 `1.55`까지 허용)을 유지하고, 숫자 열에는 반드시 Tailwind `tabular-nums` 클래스를 부여합니다.

## Layout

### Spacing System
- **기본 단위(Base unit):** `8px`. 미세 타이포그래피 보정에만 `4px, 5px, 6px`를 허용하며 모든 레이아웃 간격은 `8 / 12 / 16 / 24 / 32 / 48 / 80px` 그리드에 스냅됩니다.
- **토큰:** `{spacing.xxs}` 4px · `{spacing.xs}` 8px · `{spacing.sm}` 12px · `{spacing.md}` 17px · `{spacing.lg}` 24px · `{spacing.xl}` 32px · `{spacing.xxl}` 48px · `{spacing.section}` 80px.
- **섹션 상하 패딩:** 풀블리드 요약 타일(시뮬레이션 결과, 랜딩 소개) 내부 상하 패딩은 `{spacing.section}` (80px)이며 타일 간 마진은 `0px`(배경색 교차만으로 경계 구분)입니다.
- **카드 내부 패딩:** 모든 심사 유틸리티 카드(`{component.evaluation-utility-card}`)와 좌우 원문 대조 패널(`{component.syllabus-split-pane}`)은 `{spacing.lg}` (24px) 패딩을 기본으로 합니다.

### Grid & Container
- **최대 컨테이너 폭(Max content width):**
  - **기본 (`max-w-[1280px]`, 좌우 패딩 모바일 16px / 데스크톱 40px → 본문 1200px):** 편입생 시뮬레이션 리포트(F-09)·과목 상세·보완 서류 제출(F-06)·이의 신청, 관리자 콘솔·감사 로그, 알림 등 나머지 모든 화면. 17px 한글 본문의 한 줄 길이와 카드 비율을 지키기 위한 폭입니다.
  - **워크스페이스 확장형 (`max-w-[1440px]` → 본문 1360px):** 정보가 빽빽한 **심사관 대기열 큐(F-07, 10열 표)**와 **원문 대조 심사 화면(F-04, 교수·심사관 공통)**만 씁니다. 표의 줄바꿈과 좌우 비교 칸의 문장 꺾임을 줄이기 위한 폭입니다.
  - **구현:** `base.html`의 `{% block width %}`가 기본값 `max-w-[1280px]`이며, 상단 내비게이션·기관 보조 바·본문·푸터가 `self.width()`로 같은 폭을 공유해 좌우 정렬이 맞습니다. 확장형 화면은 템플릿에서 `{% block width %}max-w-[1440px]{% endblock %}`로 덮어씁니다. 화면 아래에 고정되는 바(`{component.floating-sticky-bar}`, `{component.selection-bar-dark}`)도 그 화면의 본문 폭에 맞춥니다.
  - **풀블리드 (`100%`):** 최상단 글로벌 내비게이션, 기관 보조 바, 푸터. 시뮬레이션 히어로는 컨테이너 안의 라운드 카드로 둡니다.
  - **학생 리포트 (2-Column `1fr : 320px`):** 왼쪽에 필터 칩과 과목 카드 목록, 오른쪽에 심사 진행 단계·계산 조건 카드(데스크톱에서 sticky). 모바일에서는 오른쪽 열이 목록 아래로 내려갑니다.
- **핵심 컬럼 패턴:**
  - **교수 심사 Split-View (2-Column 50:50):** 좌측에는 제출된 타교 강의계획서 구조화 항목(학습목표, 주차별 주제, 교재, 평가비중 F-02) 및 PDF 원문 스니펫을 배치하고, 우측에는 본교 학과 편람 매칭 후보 과목(F-03), 개념 커버리지 바, AI 3단계 추천 근거(F-05), 과거 유사 판정 이력(F-08)을 나란히 배치합니다. 컬럼 간 거터(Gutter)는 `24px`입니다.
  - **유틸리티 카드 그리드 (3~4 Column):** 학생 시뮬레이션 핵심 지표(인정 학점 / 잔여 학기 / 예상 등록금), 관리자 운영 KPI, 후보 과목 비교 카드는 `20~24px` 거터의 3~4열 그리드로 구성합니다.

### Whitespace Philosophy
Apple이 제품을 돋보이게 하기 위해 여백을 좌대(Pedestal)로 삼듯, CreditBridge_AI는 **교수의 의사결정 정확도를 높이기 위해 여백을 인지적 완충지대**로 사용합니다. 한 화면에 모든 메타데이터를 빽빽하게 우겨넣지 않고, 카드 내부 패딩 최소 `24px`, 주요 섹션 간 간격 `48~80px`, 원문 인용구 블록 상하 여백 `17px`를 엄격히 유지합니다. 정보 밀도가 가장 높은 곳은 푸터와 감사 로그 테이블뿐이며, 심사 화면에서는 항상 원문 텍스트 주위에 충분한 숨통을 확보합니다.

## Elevation & Depth

| Level | Treatment | Use in CreditBridge_AI |
|---|---|---|
| Flat | 그림자 없음, 보더 없음 | 다크 히어로 카드, 하단 다크 선택 바, 글로벌 내비게이션, 푸터, 기본 캔버스 섹션 |
| Soft hairline | `1px solid #e0e0e0` (`rgba(0, 0, 0, 0.08)`) | 심사 유틸리티 카드, 좌우 원문 대조 패널, 판정 옵션 칩, 프로스티드 서브 내비 하단 구분선 |
| Backdrop blur | `backdrop-filter: saturate(180%) blur(20px)` on Parchment 80% | 상단 `{component.sub-nav-frosted}` 및 교수 심사 화면 하단 `{component.floating-sticky-bar}` |
| Modal backdrop | 그림자 없이 `::backdrop { background: rgba(0, 0, 0, 0.5) }` + 모달 `1px solid #e0e0e0` | 불인정·판정 변경 사유 선택 창(`{component.reason-dialog}`) |
| Document shadow | `rgba(0, 0, 0, 0.22) 3px 5px 30px 0` | 캔버스 위에 띄워진 **원본 강의계획서 PDF 문서 프리뷰/모달 시트** (시스템 내 유일한 드롭 섀도우) |

**Shadow philosophy.** CreditBridge_AI는 일반 UI 카드, 버튼, 배지, 입력창에 **어떠한 드롭 섀도우(`box-shadow`)도 사용하지 않습니다.** 영역의 구분과 위계는 오직 (a) Parchment(`#f5f5f7`) 배경과 Pure White(`#ffffff`) 카드의 표면 색상 대비 + `1px` 헤어라인 보더, 그리고 (b) 상·하단 고정 바의 `backdrop-filter` 블러 효과로만 형성합니다. 시스템 내 유일한 그림자(`rgba(0, 0, 0, 0.22) 3px 5px 30px`)는 실제 종이 문서의 메타포를 가진 **원본 PDF 스캔본/문서 뷰어 시트**가 화면 위에 떠 있을 때만 적용합니다.

## Shapes

### Border Radius Scale

| Token | Value | Use in CreditBridge_AI |
|---|---|---|
| `{rounded.none}` | 0px | 풀블리드 요약 타일, 전체폭 테이블 구분선 |
| `{rounded.xs}` | 5px | 원문 내 인라인 근거 하이라이트(`<mark>`) 및 학수번호 코드 태그 |
| `{rounded.sm}` | 8px | 다크 유틸리티 버튼(CSV 내보내기, API 토큰 발급), 원문 인용구 블록(`{component.evidence-quote-block}`) |
| `{rounded.md}` | 11px | Pearl 보조 캡슐 버튼("보완 서류 요청", "과거 이력 상세"), 다크 히어로 안 메트릭 카드, 사유 선택 행, 대응 교과목 박스 |
| `{rounded.lg}` | 18px | 심사 유틸리티 카드(`{component.evaluation-utility-card}`), KPI 카드, 다크 히어로 카드, 데이터 테이블 외곽, 사유 선택 창, 하단 선택 바, 좌우 원문 대조 패널, 파일 업로드 드롭존 |
| `{rounded.pill}` | 9999px | 주요 Action Blue CTA 버튼, 판정 선택 칩(`{component.decision-option-chip}`), AI 신뢰도 배지(`{component.confidence-badge-pill}`), 검색창 |
| `{rounded.full}` | 9999px / 50% | PDF 뷰어 플로팅 원형 컨트롤 버튼(`{component.button-icon-circular}`), 진행 단계 원(`{component.progress-stepper}`), 커버리지 링, 교수 이니셜 아바타 |

### Document & Comparison Geometry
- **PDF 원본 및 스캔본 프리뷰 (F-01):** A4 또는 Letter 종횡비(약 `1 : 1.414`)를 왜곡 없이 유지하며, `{colors.canvas-parchment}` 배경 패널 중앙에 `24~40px` 내부 여백을 두고 배치합니다. 이때 문서 컨테이너에만 시스템 유일의 드롭 섀도우를 적용합니다.
- **개념 커버리지 바 (F-03):** 높이 `8px`, 모서리 `{rounded.pill}`의 수평 트랙(`#e0e0e0`) 내부에 커버리지 비율(%)만큼 채워지는 인디케이터 바를 사용합니다 (학생 과목 카드, 학과별 처리율, 월별 판정 건수).
- **커버리지 원형 게이지 (`{component.coverage-ring}`):** 표처럼 공간이 좁은 곳(심사 큐)에서는 지름 `22px`, 두께 `3px`의 링을 씁니다. `conic-gradient`로 `--p`(0~100)만큼 채우고 `mask`로 가운데를 비웁니다. 색은 75% 이상 `{colors.primary}`, 40~74% `{colors.status-elective}`, 40% 미만 `{colors.status-reject}`이며 링 옆에 `tabular-nums` 수치를 반드시 함께 적습니다(색만으로 의미를 전달하지 않음).
- **인라인 근거 하이라이트 (F-04):** 원문 텍스트 내 매칭 문장은 `{rounded.xs}` (5px) 모서리와 좌우 `4px`, 상하 `2px` 패딩을 가진 `<mark>` 요소로 감싸 문맥 흐름을 깨지 않으면서 시선을 유도합니다.

## Components

### Top Navigation

**`global-nav`** — 모든 페이지 최상단에 고정되는 초슬림 블랙 내비게이션 바. 배경 `{colors.surface-black}` (`#000000`), 높이 `44px`, 텍스트 `{colors.on-dark}` 및 `{typography.nav-link}` (12px / 400 / -0.12px). 좌측에는 **CreditBridge AI** 워드마크, 중앙에는 현재 로그인한 역할(Role)에 맞는 메뉴 항목이 `20px` 간격으로 배치됩니다(편입생: `사전 시뮬레이션` · `심사 진행현황` · `보완서류 제출` / 심사관: `심사 대기열` · `교수 배정 관리` · `SIS 내보내기` / 교수: `배정된 심사` · `과거 판정 이력` / 관리자: `운영 통계` · `문서 보존·파기` · `SIS API 토큰` · `감사 로그`). 우측에는 검색 아이콘, 알림 벨, 사용자 프로필이 위치하며 `834px` 이하에서는 햄버거 메뉴로 축약됩니다.

**`workspace-sub-bar`** (v1.1.0, 현재 구현) — 심사관·교수·관리자 화면에서 글로벌 내비게이션 바로 아래에 붙는 흰색 보조 바. 하단 `1px solid {colors.hairline}`, 높이 약 `44px`. 왼쪽에는 기관 아이콘 + 기관명(`{typography.caption-strong}`) + `/ 업무 위치`(예: `학사처 심사 워크스페이스 · 심사 대기열`, `관리자 콘솔`, muted), 오른쪽에는 HTMX로 불러오는 집계 칩(`{component.count-chip}`: `제출 요청 N` · `심사 대기 N` · `판정 완료 N`, 판정 완료만 `{component.count-chip-approve}`)을 둡니다. 학생 화면에는 표시하지 않습니다. 스크롤 시 고정하지 않습니다.

**`sub-nav-frosted`** (v1.0.0 정의, 현재 미사용) — 글로벌 내비게이션 바로 아래에 고정(Sticky)되는 컨텍스트 서브 내비게이션. 배경 `{colors.canvas-parchment}` (80% 투명도 + `backdrop-filter: saturate(180%) blur(20px)`), 높이 `52px`, 하단 `1px solid {colors.hairline}` 보더. 좌측에는 현재 화면 또는 심사 건의 타이틀(예: `"컴퓨터공학과 편입 심사 · 이지원 (2026-TR-0142)"` 또는 `"심사 대기열 큐 (미처리 18건)"`)이 `{typography.tagline}` (21px / 600)으로 표시되고, 우측에는 빠른 필터 링크(`{typography.button-utility}` 14px: `전체` · `High 신뢰도` · `보완 필요`)와 핵심 액션 버튼 `{component.button-primary}` ("판정 확정" 또는 "SIS CSV 다운로드")가 상주합니다.

### Buttons

**`button-primary`** — CreditBridge_AI의 대표 액션 시그널. 배경 `{colors.primary}` (`#0066cc`), 텍스트 `{colors.on-primary}` (`#ffffff`), 타이포그래피 `{typography.body}` (17px / 400), 모서리 `{rounded.pill}` (완전한 캡슐형), 패딩 `11px 22px`. ("판정 확정", "강의계획서 분석 시작", "보완 자료 제출").
- Active 상태 (`{component.button-primary-active}`): 색상 변경 없이 `transform: scale(0.95)` 축소 효과 적용.
- Focus 상태 (`{component.button-primary-focus}`): `2px solid {colors.primary-focus}` 아웃라인 표시.

**`button-secondary-pill`** — 주요 액션 옆에 나란히 배치되는 보조 캡슐 버튼("원본 PDF 보기", "보완 서류 요청", "재분석 실행"). 배경 투명(또는 `{colors.canvas}`), 텍스트 `{colors.primary}`, 테두리 `1px solid {colors.primary}`, 모서리 `{rounded.pill}`, 패딩 `11px 22px`.

**`page-header-card`** 속 액션 쌍 — 심사 큐 머리 카드 오른쪽에는 `{component.button-primary}`(아이콘 + "선택 항목 교수 일괄 배정")와 `{component.button-secondary-pill}`(아이콘 + "SIS CSV 내보내기")를 나란히 둡니다. 관리자 콘솔 제목 오른쪽도 같은 쌍("학사정보 연동" / "전체 감사 로그")입니다.

**`button-dark-utility`** — 데이터 내보내기 및 시스템 유틸리티 액션("SIS CSV 내보내기", "API 토큰 재발급", "감사로그 필터"). 배경 `{colors.ink}` (`#1d1d1f`), 텍스트 `{colors.on-dark}`, 타이포그래피 `{typography.button-utility}` (14px / 400), 모서리 `{rounded.sm}` (8px), 패딩 `8px 15px`. 클릭 시 `transform: scale(0.95)`.

**`button-pearl-capsule`** — 카드 내부의 중립 보조 액션("대리 심사자 지정", "유사 판정 상세 보기", "이의신청 안내"). 배경 `{colors.surface-pearl}` (`#fafafc`), 텍스트 `{colors.ink-muted-80}` (`#333333`), 타이포그래피 `{typography.caption}` (14px), 테두리 `3px solid {colors.divider-soft}`, 모서리 `{rounded.md}` (11px), 패딩 `8px 14px`.

**`button-simulation-hero`** — 편입생 입학 전 시뮬레이션 랜딩 화면의 대형 CTA 버튼("내 강의계획서로 인정 학점 시뮬레이션하기"). `{component.button-primary}`와 동일한 Action Blue 캡슐 형태이나 `{typography.button-large}` (18px / Weight 300)와 넉넉한 패딩(`14px 28px`)을 사용합니다.

**`button-icon-circular`** — PDF 원문 뷰어나 모달 위에 떠 있는 원형 아이콘 버튼(확대, 축소, 페이지 이동, 닫기). 크기 `44 × 44px`, 배경 `rgba(210, 210, 215, 0.64)`, 아이콘 `{colors.ink}`, 모서리 `{rounded.full}`.

**`text-link` & `text-link-on-dark`** — 본문 내 인라인 링크(과목 편람 원문 바로가기, 근거 문장 위치로 스크롤 이동). 라이트 표면에서는 `{colors.primary}` (`#0066cc`), 다크 타일 위에서는 `{colors.primary-on-dark}` (`#2997ff`)를 사용합니다.

### Cards & Containers

**`summary-tile-light` / `summary-tile-parchment` / `summary-tile-dark` (`-2`, `-3`)** — 풀블리드 요약 섹션 타일(모서리 `0px`, 상하 패딩 `80px`). 랜딩처럼 화면 전체를 쓰는 소개 섹션에만 씁니다.

**`summary-hero-card-dark`** (v1.1.0) — 학생 시뮬레이션 리포트(F-09) 상단의 다크 카드. 배경 `{colors.surface-tile-1}`, 모서리 `{rounded.lg}`, 패딩 `32px`(모바일) / `48px`(데스크톱).
- 첫 줄: `AI 분석 기반 예상치 · 학사처 심사 중` 같은 상태 캡션(`{colors.body-muted}`).
- 핵심 문장: `예상 인정 학점: 12.0~17.0 / 17.0 학점 (최대 100%)` — 32px(모바일) / 44px(데스크톱), 600. 인정 학점 범위만 `{colors.primary-on-dark}`, 분모와 비율은 `{colors.body-muted}`.
- 오른쪽: `출신 대학 이수 N학점 → 대상 대학 인정 N학점` 박스(`1px solid rgba(255,255,255,0.15)`, `{rounded.md}`).
- 아래: `{component.metric-card-on-dark}` 3장(졸업까지 남은 학기 / 미인정 시 추가 비용·절감액 / 심사 진행 상태 확정 수·구성), 숫자 32px `tabular-nums`.
- 마지막: 예상치이며 최종 인정은 학과 교수가 판정한다는 고지(12px, muted). 판정 확률(%)은 표시하지 않습니다.

**`page-header-card`** (v1.1.0) — 심사 큐 머리 카드. 왼쪽에 parchment 사각 아이콘(48px, `{rounded.md}`), 제목(`{기관명} 편입 학점 심사 대기열`, `{typography.display-md}`)과 `미처리 N건` reject 배지, 아래 보조 정보(muted). 오른쪽에 액션 쌍.

**`kpi-card`** & **`stat-tile`** (v1.1.0) — 관리자 콘솔·심사 큐 핵심 지표. `kpi-card`는 흰 카드(`1px` 헤어라인, `{rounded.lg}`, 패딩 `20px`)에 라벨(14px muted) → `{typography.kpi-number}` 수치(단위는 17px muted) → 선택적 커버리지 바 → 근거 캡션(12px muted) 순서입니다. 보조 지표는 테두리 없는 parchment `stat-tile`(24px 수치)로 한 단계 낮춰 보여줍니다. 수치에는 근거(예: `정보 부족 제외 첫 판정 4건 기준`)를 함께 적고, 실제 데이터가 없는 증감률·인증 배지는 넣지 않습니다.

**학과별 처리 지표 카드** — `{component.evaluation-utility-card}` 3열 그리드. 학과명(600) + `판정/접수 건수`, 커버리지 바로 처리율, 하단에 `처리율 %` · `평균 N일`.

**`data-table`** (v1.1.0) — 심사 큐·감사 로그 표. 흰 카드 외곽(`{rounded.lg}`, 내부 패딩 0), 헤더 행 `{colors.surface-pearl}` 배경 + 12~14px 헤더, 행 구분 `1px solid {colors.divider-soft}`. 좁은 화면에서는 표 전체를 가로 스크롤(`min-width`)로 두고 페이지는 가로로 넘치지 않게 합니다. 심사 큐는 일관성 경보가 있는 행 바로 아래에 `{colors.surface-reject-subtle}` 배경의 인라인 경보 행(`[일관성 경보] …` + `과거 판례 N건 보기` 링크)을 붙이고, 정보 부족 행은 `{colors.surface-elective-subtle}`를 옅게 깝니다. 담당 교수는 `{component.avatar-initial}`(이니셜 원, 28px) + `학과 이름` + `배정 완료/대리 재배정` 캡션으로 표시합니다. 표 아래에 `대기열 N건 중 a–b 표시 · p / n 페이지`와 이전/다음 링크를 둡니다.

**`progress-stepper`** (v1.1.0) — 학생 리포트 오른쪽 `심사 진행 현황`(서류 접수 → AI 구조화·근거 추출 → 학과 교수 심사 → 최종 확정). 단계 원 24px: 완료는 `{colors.primary}` 채움 + 체크, 진행 중은 `2px` primary 테두리 + 번호 + `진행 중` 라벨, 대기는 헤어라인 테두리 + muted 번호. 단계 사이 세로선은 완료 구간만 primary. 교수 심사 단계에는 `확정 수 / 전체` 캡션과 커버리지 바를 붙입니다.

**학생 과목 카드** (v1.1.0) — `{component.evaluation-utility-card}` 안에 상태 라벨(`승인 완료 · 직접 인정` approve, `보완 필요` elective, `심사 중`/`AI 추천` 중립 + 추천 배지, `불인정` reject) → 과목 코드·이름(19px/600, 상세 링크) → 파일·학점·성적 캡션, 오른쪽에 개념 커버리지 수치(28px, 색은 커버리지 구간), 아래에 parchment `대응 교과목` 박스(코드·이름·학과 / 판정 교수 또는 담당 교수·판정일), 커버리지 바, 진행 단계 점을 둡니다. 보완이 필요한 과목은 카드 테두리를 elective로 바꾸고 `정보 부족 진단` 콜아웃(요청 항목, 확인되지 않은 개념, 필요한 자료 + `보완 서류 제출하기` primary 버튼)을 넣습니다.

**`evaluation-utility-card`** — 심사 대기열 항목, 후보 과목 매핑 카드(F-03), 부족 정보 진단 카드(F-06), 관리자 통계 카드의 기본 컨테이너. 배경 `{colors.canvas}` (`#ffffff`), 테두리 `1px solid {colors.hairline}` (`#e0e0e0`), 모서리 `{rounded.lg}` (18px), 패딩 `{spacing.lg}` (24px). 그림자는 없으며 상단에 과목명/학수번호(`{typography.body-strong}` 17px/600), 중앙에 개념 커버리지(%) 게이지와 핵심 요약(`{typography.body}` 17px/400), 하단에 `{component.confidence-badge-pill}` 및 `{component.text-link}` ("원문 대조 심사하기 →")를 배치합니다.

**`syllabus-split-pane`** — 학과 교수 심사 화면(F-04)의 핵심인 **좌우 1:1 원문 비교 패널**. 각 패널은 `{colors.canvas}` 배경, `1px solid {colors.hairline}` 테두리, `{rounded.lg}` (18px) 모서리, `24px` 패딩을 가집니다.
- **좌측 패널 (Submitted Syllabus):** F-02를 통해 추출된 타교 강의계획서의 학습목표, 1~16주차 강의 주제, 교재, 선수과목, 평가 기준 및 PDF 원문 발췌본을 표시하며, 매칭 근거 문장은 `{colors.highlight-evidence-source}` (`#fff8c5`)로 하이라이트됩니다.
- **우측 패널 (Target University Catalog):** 본교 학과 편람에서 필터링된 상위 후보 과목(F-03)의 요강과 주차별 주제를 표시하며, 대응되는 근거 문장은 `{colors.highlight-evidence-target}` (`#e6f2ff`)로 하이라이트되어 교수가 AI 환각(Hallucination) 여부를 즉각 검증할 수 있습니다.

**`evidence-quote-block`** — F-04의 검증된 원문 인용구(Exact Quote)를 담는 전용 블록. 배경 `{colors.canvas-parchment}` (`#f5f5f7`), 좌측 `3px solid {colors.primary}` 포인트 보더, 모서리 `{rounded.sm}` (8px), 패딩 `17px 24px`. 원문과 100% 일치함이 프로그래밍적으로 검증된 인용구 옆에 `"원문 일치 검증됨 (Page 2, Week 5)"` 캡션을 함께 표기합니다.

**`decision-option-chip` & `decision-option-chip-selected`** — Apple 스토어의 기기 옵션 선택 칩 문법을 계승한 **판정 및 필터 선택 칩**. 배경 `{colors.canvas}`, 텍스트 `{colors.ink}` (`{typography.caption}` 14px), 기본 테두리 `1px solid {colors.hairline}`, 모서리 `{rounded.pill}`, 패딩 `12px 16px`.
- 활용처: (1) 교수의 최종 판정 선택(`AI 추천대로 승인` · `수정` · `반려(불인정)`). 사유 선택은 v1.1.0부터 칩이 아니라 `{component.reason-dialog}` 안의 행으로 받습니다.
- 선택 상태(`{component.decision-option-chip-selected}`): 배경색을 바꾸지 않고 테두리를 `2px solid {colors.primary-focus}` (`#0071e3`)로 두껍게 변경하여 Apple 컨피규레이터와 동일한 깔끔한 선택 피드백을 제공합니다.

**`filter-chip` & `filter-chip-selected`** (v1.1.0) — 목록을 거르는 탭형 칩(심사 큐 `전체 · 고신뢰 · 저신뢰 · 정보 부족 · 일관성 경보`, 학생 리포트 `전체 · 승인 완료 · 보완 필요 · 심사 중`). 높이 `36px`, `{rounded.pill}`, `1px` 헤어라인, 라벨 뒤에 muted 건수. 선택 상태는 **잉크 채움**(`{colors.ink}` 배경 + 흰 글자, 건수는 70% 흰색)으로, 판정 칩의 파란 테두리 선택과 구분합니다(필터는 "지금 보는 범위", 판정 칩은 "내가 내릴 결정"). `일관성 경보` 칩에는 6px reject 점을 붙입니다. 두 번째 축(학과 필터)은 세로 구분선 뒤에 13px 칩으로 두고, 선택 시 `{colors.primary-focus}` 테두리 + 링을 씁니다. 검색창(`{component.search-input}`)은 같은 줄 왼쪽에 둡니다.

**`count-chip`** (v1.1.0) — 보조 바의 읽기 전용 집계(`제출 요청 2`). 흰 배경, `1px` 헤어라인, 12px, 숫자만 600 `tabular-nums`.

**`confidence-badge-pill`** — AI 신뢰도(High / Medium / Low), 3단계 추천 등급(F-05), 과거 판정 유사도(`유사도 88% · 과거 인정`)를 표시하는 읽기 전용 캡슐 배지. 모서리 `{rounded.pill}`, 패딩 `4px 12px`, 타이포그래피 `{typography.caption-strong}` (14px / 600). 의미에 따라 앞서 정의한 시맨틱 배경/텍스트 컬러 쌍(`approve`, `elective`, `reject`, 또는 중립 `surface-pearl`)을 적용합니다.

**`upload-dropzone-card`** — F-01 국·영문 디지털/스캔 PDF 강의계획서 업로드 영역. 배경 `{colors.canvas-parchment}`, 테두리 `1px dashed {colors.ink-muted-48}` (드래그 오버 시 `2px solid {colors.primary-focus}`), 모서리 `{rounded.lg}` (18px), 패딩 `48px`. 중앙 정렬된 문서 아이콘, 안내 타이틀(`{typography.tagline}`), 지원 규격 안내(`"디지털 또는 스캔 PDF · 한국어/영어 자동 인식(OCR) · 별도 번역 불필요"`), 그리고 `{component.button-primary}` ("파일 선택")으로 구성됩니다.

**`selection-bar-dark`** (v1.1.0) — 심사 큐에서 행을 하나 이상 고르면 화면 아래(`bottom: 16px`)에 떠오르는 다크 바. 배경 `{colors.surface-tile-1}`, `{rounded.lg}`, 패딩 `12px 20px`, 그림자 없음. 왼쪽에 `{colors.primary-on-dark}` 점 + `N건 선택됨` + 설명(muted), 오른쪽에 `{component.button-primary}`("담당 교수 일괄 배정")와 선택 해제 텍스트 버튼. 선택이 0건이면 숨깁니다.

**`floating-sticky-bar`** — 교수 심사 화면 및 모바일 승인 뷰(F-07)에서 화면 하단에 고정되는 프로스티드 액션 바. 배경 `{colors.canvas-parchment}` (80% 투명도 + `backdrop-filter: saturate(180%) blur(20px)`), 상단 `1px solid {colors.hairline}`, 높이 `64px`, 패딩 `12px 32px`. 바의 배경은 화면 전체 폭이고, 안쪽 내용은 본문과 같은 `max-w-[1440px]` + 좌우 `40px` 패딩으로 정렬합니다.
- 좌측: 현재 검토 중인 과목 매칭 요약(예: `"타교 Data Structures (3학점) → 본교 자료구조 (3학점) · 개념 커버리지 86%"`) 및 과거 유사 판정 충돌 시 F-08 경고 배지 표시.
- 우측: `{component.button-secondary-pill}` ("보완 자료 요청") + `{component.button-primary}` ("최종 판정 확정").

### Inputs & Forms

**`search-input`** — 심사 대기열 검색, 본교 과목 편람 검색, 감사 로그 조회에 사용되는 캡슐형 검색창. 배경 `{colors.canvas}`, 텍스트 `{colors.ink}` (`{typography.body}` 17px), 테두리 `1px solid rgba(0, 0, 0, 0.08)` (포커스 시 `2px solid {colors.primary-focus}`), 모서리 `{rounded.pill}`, 패딩 `12px 20px`, 높이 `44px`.

**`reason-dialog` — 사유 선택 및 소명 창 (v1.1.0, FR-09·FR-11):**
- **언제 여는가:** 교수가 판정 확정을 누를 때 (a) `반려`, (b) AI 추천과 다른 `수정`(등급 또는 직접 인정 대상 과목이 다름), (c) 같은 대상 과목·유사 강의계획서의 과거 판정과 결과가 다를 때만 엽니다. AI 추천대로 승인하고 경보도 없으면 창 없이 바로 확정합니다.
- **모양:** 네이티브 `<dialog>`(폭 `min(640px, 100% - 32px)`, 최대 높이 화면 - 32px, 내부 스크롤), `{rounded.lg}`, `1px` 헤어라인, 그림자 없이 50% 검정 backdrop. 머리: reject-subtle 원형 경고 아이콘 + 제목(`학점 불인정 사유 선택 및 소명` / `판정 변경 사유 선택 및 소명` / `과거 판정과 다른 결과 확인`, 21px/600) + `출신 과목 → 후보 과목 · AI 추천` 캡션 + 닫기 원형 버튼.
- **본문:** (1) 경보가 있으면 elective 콜아웃(`일관성 경보`, 과거 판정 N건 문장, `과거 판정 이력 보기` 링크, `과거 판정을 확인했고 이 판정으로 확정합니다` 체크박스). (2) 사유 행 `{component.reason-option-row}`: 체크박스 + 사유 이름(17px/600) + 한 줄 설명(14px muted, `decisions.REASON_HINTS`). 선택된 행은 `{component.reason-option-row-selected}`(reject-subtle 배경 + reject 50% 테두리, CSS `:has(:checked)`). (3) 소명 메모 textarea(`maxlength=500`, 오른쪽 위 `n/500` 글자 수, `기타` 선택 시 필수).
- **바닥:** pearl 배경 바에 `{component.button-secondary-pill}` "취소 / 판정 변경"(창을 닫고 판정을 다시 고름)과 `{component.button-primary}` "불인정 사유 저장 및 판정 확정"(수정이면 "사유 저장 및 판정 확정", 경보만 있으면 "확인하고 판정 확정"). 버튼 색은 반려여도 Action Blue를 유지합니다.
- **검증 실패:** 서버가 422(사유 누락 등)나 409(경보 미확인)를 돌려주면 같은 창을 자동으로 다시 열고 맨 위에 reject-subtle 에러 문장을 보여줍니다. 판정 칩·등급 선택 오류처럼 창과 무관한 에러는 판정 카드 안에 표시합니다.

### Footer

**`footer`** — 배경 `{colors.canvas-parchment}` (`#f5f5f7`), 상단 `1px` 헤어라인, 패딩 `32px`, 텍스트 `{colors.ink-muted-80}` `{typography.fine-print}` (12px). 첫 줄은 primary 방패 아이콘 + **"Human-in-the-Loop 고지:"**(ink, 600) + "본 시스템의 AI 분석 결과는 심사 참고용 근거 자료이며, 최종 학점 인정 여부는 해당 학과 교수의 승인으로 확정됩니다.", 둘째 줄은 `{colors.ink-muted-48}`로 제출 문서 보존/파기 안내와 저작권 표기입니다. 링크 컬럼은 두지 않습니다.

## Do's and Don'ts

### Do
- 모든 클릭 가능한 인터랙티브 요소(주요 CTA 버튼, 텍스트 링크, 포커스 링, 선택된 판정 칩 테두리)에는 오직 **`{colors.primary}` (Action Blue `#0066cc`) 계열**만 사용하세요.
- 헤드라인은 `{typography.hero-display}` 또는 `{typography.display-lg}`에 네거티브 자간(`-0.28px ~ -0.374px`)을 적용하여 단정하고 신뢰감 있는 학술 SaaS의 인상을 유지하세요.
- 강의계획서 원문, 편람 설명, 심사 의견 등 모든 본문 텍스트는 **17px (`{typography.body}`, 행간 1.47)**로 설정하여 장시간 심사 시 가독성을 확보하세요.
- 대시보드 배경에는 `{colors.canvas-parchment}` (`#f5f5f7`)를 깔고, 그 위에 `{colors.canvas}` (`#ffffff`)와 `1px solid {colors.hairline}`을 가진 `{component.evaluation-utility-card}` 및 `{component.syllabus-split-pane}`을 배치하여 그림자 없이 깔끔한 레이어 구분을 만드세요.
- 학점 수, 개념 커버리지(%), 유사도(%), 예상 등록금 등 모든 수치 데이터에는 `tabular-nums`를 적용하세요.
- 모든 버튼의 클릭(Active) 상태에는 색상 변화 대신 `transform: scale(0.95)` 마이크로 인터랙션을 일관되게 적용하세요.

### Don't
- Action Blue 외에 두 번째 브랜드 버튼 색상을 만들지 마세요. 초록색("승인 버튼")이나 빨간색("반려 버튼")으로 솔리드 버튼을 칠하지 말고, 판정 옵션은 `{component.decision-option-chip}`으로 선택한 뒤 최종 제출은 단일 `{component.button-primary}` (Action Blue "판정 확정")으로 수행하세요. **유일한 예외:** 심사 큐에서 일관성 경보가 걸린 행의 `충돌 내역 확인` 버튼은 판정이 아니라 경보 이력으로 이동하는 링크이므로 `{colors.status-reject}` 채움을 허용합니다.
- 실제 데이터가 없는 장식 요소를 넣지 마세요: 인증 배지(FERPA·SOC2 등), 전주 대비 증감, 판정 확률(%), 해시 체인 표시, 상담 담당자 카드 등. 교수·관리자 화면에 학생 이름을 노출하지 마세요(감사 로그 처리자도 학생은 `학생`으로 표시).
- 일반 카드, 테이블, 버튼, 텍스트에 드롭 섀도우(`box-shadow`)를 넣지 마세요. 그림자는 오직 캔버스 위에 떠 있는 **원본 PDF 문서 프리뷰**에만 허용됩니다.
- 배경에 장식적인 CSS 그라데이션을 넣지 마세요.
- 본문이나 타이틀에 `font-weight: 500`을 사용하지 마세요 (`300 / 400 / 600 / 700` 체계 엄수).
- AI가 생성한 요약문만 단독으로 보여주지 마세요. F-04 원칙에 따라 반드시 좌우 원문 인용구 하이라이트(`{colors.highlight-evidence-source}`, `{colors.highlight-evidence-target}`)를 함께 노출해야 합니다.
- 라이트 배경(`#ffffff`, `#f5f5f7`) 위에서 다크 전용 링크 컬러인 `{colors.primary-on-dark}` (`#2997ff`)를 사용하지 마세요(명도 대비 부족). 라이트 표면에서는 항상 `#0066cc`를 사용합니다.

## Responsive Behavior

### Breakpoints

| Name | Width | Key Changes in CreditBridge_AI |
|---|---|---|
| Small phone | ≤ 419px | 모바일 교수 승인 뷰(F-07): 단일 컬럼 스택; 서브 내비게이션은 과목명+확정 CTA만 유지; 히어로 수치 28px로 축소 |
| Phone | 420–640px | 좌우 원문 대조 패널(`syllabus-split-pane`)이 상하 탭 전환(원문 보기 ↔ 본교 편람 보기) 또는 아코디언 스택으로 전환; 하단 `floating-sticky-bar` 상시 고정 |
| Large phone | 641–735px | 요약 타일 상하 패딩 축소(`80px → 48px`); 심사 대기열 테이블이 모바일 카드 리스트 형태로 변환 |
| Tablet portrait | 736–833px | 글로벌 내비게이션이 햄버거 메뉴로 접힘; 서브 내비게이션의 세부 필터 칩이 드롭다운으로 수납 |
| Tablet landscape | 834–1023px | 글로벌 내비게이션 전체 노출 복귀; 좌우 1:1 원문 대조 Split-View 활성화 시작; 3열 유틸리티 그리드는 2열로 배치 |
| Small desktop | 1024–1068px | 교수 심사 Split-View(좌우 패널) 및 심사관 큐 테이블 전체 컬럼 표시; 타이틀 40px 유지 |
| Desktop | 1069–1440px | 기본 표준 워크스페이스 레이아웃; 3~4열 시뮬레이션/관리자 KPI 그리드; 기본 화면은 `1280px`에서 멈추고 심사 큐·원문 대조 화면은 `1440px`까지 넓어짐 |
| Wide desktop | ≥ 1441px | 콘텐츠 최대 폭(기본 `1280px`, 확장형 `1440px`)을 고정하고 남는 폭은 좌우 여백으로 흡수 |

### Touch Targets
- 모바일에서도 학과 교수가 즉시 승인·반려·보완요청(F-07 모바일 승인 지원)을 처리할 수 있도록 모든 터치 타겟은 최소 **`44 × 44px`** 이상을 보장합니다.
- `{component.button-primary}`, `{component.decision-option-chip}`, `{component.search-input}`, `{component.button-icon-circular}` 모두 높이 `44px` 이상으로 설계되어 모바일 오터치를 방지합니다.

### Collapsing Strategy
- **Global nav**: 데스크톱에서는 역할별 전체 메뉴 가로 나열 → `833px` 이하에서는 좌측 로고 + 우측 알림/햄버거 아이콘으로 축약.
- **Sub-nav**: 심사 건 제목 + 신뢰도 필터 + 주요 CTA → 모바일에서는 심사 건 학수번호/과목명 + 우측 주요 CTA만 남기고 필터는 트레이로 이동.
- **교수용 원문 대조 뷰 (`syllabus-split-pane`)**: 데스크톱(`≥834px`)에서는 좌우 50:50 나란히 비교 → 모바일(`≤833px`)에서는 매칭된 근거 쌍(Evidence Pair) 단위로 `[제출 강의계획서 원문 인용] ↕ [본교 편람 대응 문장]`이 위아래로 맞물리는 카드 스택으로 전환하여 가로 스크롤 없이 한눈에 비교 가능하게 처리.
- **Utility grids** (시뮬레이션 지표, 후보 과목 카드, 관리자 KPI): 4열 → 3열(`≥768px`) → 2열 → 1열(`<640px`).
- **심사 큐 표**: 카드로 바꾸지 않고 `min-width: 1080px` 표를 카드 안에서 가로 스크롤합니다. 필터 칩은 줄바꿈으로 쌓습니다.
- **사유 선택 창**: 모바일에서도 같은 창을 화면 폭 - 32px로 띄우고 내부를 스크롤합니다.

### Document & Split-View Behavior
- 원본 강의계획서 PDF 뷰어는 지연 로딩(Lazy-loading)으로 페이지별 렌더링 이미지(WebP/PNG)를 불러오며, 인용 근거 문장 클릭 시 HTMX 또는 경량 스크립트를 통해 해당 PDF 페이지 및 주차(Week) 위치로 즉시 스크롤 포커스됩니다.
- 다국어(국·영문) 텍스트가 긴 과목명이나 학습목표도 말줄임표(`...`)로 잘라내지 않고 줄바꿈(`word-break: keep-all`, `overflow-wrap: break-word`)을 허용하여 심사 근거가 누락되지 않게 합니다.

## Iteration Guide (Jinja2 + HTMX + Tailwind CSS 구현 지침)

1. **한 번에 하나의 컴포넌트 단위로 작업하세요.** 템플릿 작성 시 YAML에 정의된 컴포넌트 키(`{component.syllabus-split-pane}`, `{component.decision-option-chip}`, `{component.floating-sticky-bar}`)를 기준으로 Jinja2 파셜(Partial/Macro)을 분리합니다.
2. **인라인 Hex 코드 대신 토큰/테일윈드 변수를 사용하세요.** `tailwind.config.js` 또는 CSS 변수에 본 문서의 `colors`, `typography`, `rounded`, `spacing` 토큰을 등록하고 참조합니다.
3. **Hover 상태에 의존하지 마세요.** 모바일 승인(F-07)과 데스크톱 환경을 동시에 지원해야 하므로 모든 상태 변화는 Default, Focus(`2px solid #0071e3`), Selected(`2px solid #0071e3`), Active(`scale(0.95)`)로 명확히 정의합니다.
4. **HTMX 부분 교체(`hx-get`, `hx-post`, `hx-swap`) 시 레이아웃 시프트를 방지하세요.** AI 신뢰도 필터링, 후보 과목 전환, 과거 유사 판정 충돌 경고(F-08) 노출 시 카드 테두리(`1px solid #e0e0e0`)와 패딩(`24px`) 규격을 유지한 채 내부 컨텐츠만 교체합니다.
5. **강조가 필요할 때는 장식(테두리 색상 남발, 그림자 추가) 대신 표면 색상을 교차하세요.** 기본 캔버스(`#f5f5f7`) 위의 흰색 카드(`#ffffff`), 또는 핵심 요약 영역의 다크 타일(`#272729`) 전환만으로 충분한 시각적 집중도를 얻을 수 있습니다.

## Known Gaps & Domain Considerations

- **OCR 스캔 품질 저하 문서 표시 (F-01/F-06):** 저해상도 스캔 PDF로 인해 특정 주차의 텍스트 추출 신뢰도가 낮을 경우, 원문 대조 패널 내 해당 블록을 `{colors.surface-elective-subtle}` (`#fef5e7`) 배경으로 표시하고 원본 PDF 이미지 스니펫을 인라인으로 함께 노출하는 폴백 UI가 필요합니다.
- **다크 모드 지원 범위:** 본 디자인 시스템은 Apple 스토어 및 학술 문서 열람 환경과 마찬가지로 **라이트/파치먼트 중심(Daytime-dominant)**에 부분 다크 요약 타일을 결합한 하이브리드 구조입니다. 전체 화면 다크 모드는 장문의 PDF 강의계획서 대조 시 가독성 편차를 유발할 수 있어 기본 스펙에서는 제외합니다.
- **차트 및 통계 시각화 (기관 관리자 대시보드):** 차트 라이브러리를 쓰지 않고 커버리지 바(`meter`)로 학과별 처리율·AI 추천 수용률·월별 판정 건수를 그립니다. 관리자 화면의 학과별 심사 처리율 및 AI 추천 수용률 차트는 별도의 화려한 차트 컬러 팔레트를 도입하지 않고, `{colors.primary}` (`#0066cc`), `{colors.ink}` (`#1d1d1f`), `{colors.surface-chip-translucent}` (`#d2d2d7`), 그리고 3가지 시맨틱 상태 컬러만으로 절제되게 표현합니다.
