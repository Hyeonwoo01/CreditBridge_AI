# CreditBridge

편입 준비생을 위한 **학점 인정 예측 앱**입니다. 전적 대학의 강의계획서(Syllabus)를 올리면 편입 희망 대학의 어떤 과목으로 인정될지 일치율과 근거 구절을 함께 보여줍니다.

## 할 수 있는 것

1. **강의계획서 올리기**: PDF·TXT 파일을 올리거나 텍스트를 붙여넣습니다. 여러 과목을 한 번에 올릴 수 있습니다.
2. **자동 추출**: 과목명, 학점, 학습 목표, 주차별 주제, 교재, 선수 과목, 평가 방식을 정형 데이터로 뽑아냅니다.
3. **과목 매핑**: 희망 대학 카탈로그의 단원과 비교해 대체 과목 후보와 일치율(%)을 계산합니다.
4. **근거 확인**: "Hanbit University 4–6주차 내용이 MATH 1A의 '도함수' 단원과 100% 일치"처럼 단원별 근거를 보여주고, 강의계획서의 해당 구절을 하이라이트합니다.
5. **주의사항 표시**: 학점이 부족한 경우, 성적이 C 미만인 경우, 다루지 않은 단원이 있는 경우를 알려줍니다.
6. **편입 플랜**: 인정 예상 학점, 단축 가능한 학기 수, 절감되는 등록금을 계산합니다. 어드바이저에게 낼 근거 리포트도 인쇄할 수 있습니다.

데이터는 모두 브라우저(localStorage)에만 저장됩니다.

## 실행

```bash
npm install
npm run dev            # http://localhost:5173
```

### AI 분석 (선택)

`.env.example`을 `.env`로 복사하고 `ANTHROPIC_API_KEY`를 넣으면 Claude가 강의계획서를 분석합니다. 비정형 양식이나 한국어 강의계획서도 처리할 수 있습니다.
키가 없으면 브라우저 안의 규칙 기반 파서로 분석하며, 이 경우 상단에 `오프라인 분석`이라고 표시됩니다.

### 프로덕션

```bash
npm run build
npm start              # http://localhost:3000 (PORT로 변경 가능)
```

## 구조

```
src/
  App.tsx                  화면 전환 · 상태 관리
  components/              과목 분석 / 과목 상세 / 편입 플랜 화면
  lib/extract.ts           규칙 기반 강의계획서 파서
  lib/match.ts             단원별 일치율 계산 · 근거 구절 수집
  lib/plan.ts              인정 학점 · 학기 · 등록금 계산
  lib/pdf.ts               브라우저 PDF 텍스트 추출 (pdf.js)
  data/catalog.ts          편입 희망 대학 카탈로그 (샘플)
  data/samples.ts          체험용 샘플 강의계획서
server/
  extract.ts               Claude 구조화 출력으로 강의계획서 추출
  api.ts                   /api/health, /api/extract
  index.ts                 프로덕션 서버
```

```bash
npm test        # 파서 · 매칭 테스트
npm run typecheck
```

## 참고

- 카탈로그(UC Berkeley, UT Austin, University of Michigan)는 **데모용 샘플**입니다. 과목 코드는 실제 체계를 참고했지만 단원 구성과 학점당 등록금은 예시 값입니다. 학교를 추가하려면 `src/data/catalog.ts`에 항목을 추가하세요.
- 결과는 예측치입니다. 최종 인정 여부는 대학 학사처와 학과의 심사로 결정됩니다.

## 디자인

[`docs/DESIGN-airbnb.md`](docs/DESIGN-airbnb.md) 토큰을 따릅니다. 흰 배경에 단일 포인트 컬러(Rausch `#ff385c`)를 쓰고, 알약 모양 검색바, 14px 라운드 카드, 64px 일치율 숫자를 사용합니다. 모바일에서는 하단 탭 바, 데스크톱에서는 상단 탭으로 바뀝니다.
