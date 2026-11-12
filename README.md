# CreditBridge AI

[![CI](https://github.com/Hyeonwoo01/CreditBridge_AI/actions/workflows/ci.yml/badge.svg)](https://github.com/Hyeonwoo01/CreditBridge_AI/actions/workflows/ci.yml)

**편입생의 강의계획서를 AI가 분석해 "어떤 과목으로 학점이 인정될지"를 원문 근거와 함께 추천하고, 최종 판정은 학과 교수가 내리는 편입 학점 심사 플랫폼**

**배포 사이트**: https://creditbridge-hw.duckdns.org (테스트 계정은 [아래](#사이트-둘러보기))

`Python 3.12` `FastAPI` `PostgreSQL 17` `Celery + Redis` `Jinja2 + HTMX + Tailwind` `Claude / GPT` `AWS EC2·RDS·S3` `Docker`

| 학생: 성적표를 올리면 과목마다 요청이 생기고 예상 인정 학점을 미리 봄 | 교수: 양쪽 강의계획서의 원문 근거를 나란히 보고 판정 |
| --- | --- |
| ![학생 홈](docs/images/student-home.png) | ![근거 비교](docs/images/evidence.png) |
| **심사관: 신뢰도·정보 부족·일관성 경보로 걸러 교수에게 배정** | **관리자: 지어낸 인용 비율·교수 확인 정확도 같은 AI 근거 품질 지표** |
| ![심사 대기열](docs/images/review-queue.png) | ![AI 근거 품질](docs/images/ai-quality.png) |

## 풀려는 문제

해외 대학에서 미국 4년제로 편입하면, 이미 들은 과목이 편입 대학의 어떤 과목으로 인정되는지 학과 교수가 강의계획서를 한 장씩 대조해 정합니다. 결과가 나오기까지 몇 주가 걸려 학생은 수강 신청 전에 결과를 모르고, 같은 과목을 다시 듣기도 합니다([페르소나](docs/spec.md)).

AI에게 판정을 맡기면 빠르지만, AI는 강의계획서에 없는 내용을 그럴듯하게 지어낼 수 있고 학점 인정의 책임을 질 수도 없습니다. 그래서 **AI는 원문 근거가 확인된 추천만 하고, 판정은 반드시 사람이 내리도록** 설계했습니다.

## 기술적으로 신경 쓴 점

1. **AI 환각을 코드로 걸러냄**: AI가 인용한 구절이 원문에 그대로 있는지 대조해 없으면 버리고, 선수과목·교재 칸이나 "다루지 않음" 같은 문장은 근거로 치지 않습니다. 근거가 확인되지 않은 개념은 커버리지 40%를 넘지 못합니다. 버린 인용 비율은 프롬프트 버전별로 기록해, 프롬프트를 바꿨을 때 환각이 줄었는지 비교합니다. ([evidence.py](backend/ai/evidence.py), [scoring.py](backend/services/scoring.py))
2. **최종 판정은 사람만**: 판정에는 판정한 교수가 반드시 남고, 판정·감사 기록은 고치거나 지우지 않고 추가만 합니다(이의 신청 재판정도 새 기록). 교수는 인정 학점 수까지 확정하고(여러 출신 과목을 합쳐 하나로 인정할 수 있고, 같은 학점을 두 번 쓰거나 같은 과목을 두 번 인정하지 못하게 승인된 배분 원장으로 관리, 대학마다 다른 학점 단위는 관리자가 승인한 환산 규칙으로만 바꾸고, 규칙이 없으면 숫자를 지어내지 않고 보류), AI 추천과 다르게 판정하면 선택형 사유를 남기고, 비슷한 강의계획서에 과거와 다른 결과를 내리려 하면 확정 전에 경보를 띄웁니다. 인정 최저 성적·편입 학점 상한 같은 학칙은 대학·학과·입학연도별 승인된 정책으로만 적용하고, 판정 때의 정책·과목·환산 규칙·증거 상태를 판정 기록에 함께 남겨 나중에 규칙이 바뀌어도 그 판정을 그대로 재현합니다. 두 사람이 같은 심사 건을 동시에 고치면 덮어쓰지 않고 알리며, 이의 신청은 원 판정 교수가 아닌 교수가 다시 봅니다.
3. **같은 입력이면 같은 결과**: 같은 문서는 AI를 다시 부르지 않고, 추천 등급·신뢰도는 AI가 아니라 코드 한 곳의 고정 규칙으로 계산합니다. 프롬프트나 규칙을 바꾸면 버전을 올리고, 결과 재사용 키에 버전이 들어가 이전 결과와 섞이지 않습니다.
4. **개인정보와 보안**: 글자로 된 성적표는 이름·학번을 가린 뒤 AI에 보내고, 문서 속 "이 과목을 인정하라" 같은 지시 문구는 데이터로만 다룹니다(프롬프트 인젝션 방지). PDF에 흰 글씨·투명 글자로 숨긴 문장은 AI에 보내지 않고, JavaScript·첨부 파일이 든 PDF나 확장자를 속인 파일은 받지 않습니다. 다른 대학 계정이 우리 대학 문서 번호를 알아도 열거나 바꿀 수 없는지 테스트로 확인합니다. CSRF, 보안 헤더, 로그인 실패 제한, 업로드 크기·쪽수 상한, 문서 삭제 요청 처리도 넣었습니다.
5. **운영할 수 있는 구조**: AI 분석은 Celery로 비동기 처리하고, 서버가 다시 시작돼도 멈춘 작업을 이어서 처리합니다. 스키마는 Alembic 마이그레이션으로만 바꾸고, 화면은 한국어·영어를 지원합니다. 테스트 약 370개(단위 + PostgreSQL 통합, 학점 계산·문서 추출 회귀 표와 프롬프트 인젝션 공격 문구 모음 포함)는 푸시할 때마다 GitHub Actions에서 lint·타입 검사와 함께 돌고, AWS 프리티어(EC2·RDS·S3)에 배포했습니다.

## AI와 함께 개발한 방식

코드는 AI 코딩 도구(Claude Code)와 함께 작성했습니다. 무엇을 만들지와 어떤 규칙을 지킬지는 제가 정하고, AI는 그 규칙 안에서 코드·테스트·문서를 쓰게 했습니다.

- **제가 정한 것**: 문제 정의와 기획(페르소나·기능 명세·테스트 명세·기술 스택, [docs/spec.md](docs/spec.md)), 그리고 업무 규칙입니다. 예를 들어 성적 C 이상만 심사, 성적표를 먼저 올리면 과목마다 요청을 자동으로 만들기, 편입 학점 상한, 문서를 지우면 이의 신청까지 정리하기, AI 근거를 어디까지 믿을지 같은 기준입니다.
- **규칙으로 묶은 것**: [CLAUDE.md](CLAUDE.md)에 고정 스택(목록 밖 라이브러리는 추가 전에 사람에게 묻기), 코드 구조(SQL·AI 호출·추천 규칙을 둘 곳), 꼭 지킬 것(판정은 사람만, 판정 기록은 추가만, 근거는 원문과 일치할 때만, 로그에 개인정보 금지), 작업 완료 전 검사를 적어 두고 AI가 매번 따르게 했습니다.
- **검증한 방법**: 모든 변경은 lint·타입 검사·테스트를 통과해야 커밋하고, GitHub Actions가 다시 확인합니다. 큰 변경 뒤에는 실제 브라우저로 역할별 화면을 눌러 보는 시뮬레이션을 돌렸고, 이 과정에서 근거 필터가 정상 문장("quiz in the following class" 등)을 버리던 오판을 찾아 고쳤습니다.
- **직접 써 보고 고친 것**: 화면을 직접 써 보며 찾은 문제를 고쳤습니다. 예를 들어 문서 삭제로 끝난 요청이 판정 확정 수에 들어가던 문제, 문서를 지워도 이미 낸 이의 신청이 남던 문제, 할 일 목록이 과목마다 길게 늘어나던 문제입니다.
- **배포와 운영**: AWS 콘솔에서 EC2·RDS·S3를 만들어 배포했고, 쓰지 않을 때 비용이 나가지 않게 AWS가 7일 뒤 자동으로 켜는 DB를 다시 끄는 Lambda를 붙였습니다. 비밀번호·API 키는 저장소에 두지 않습니다.
- **이해하고 넘어가기**: 모르는 부분은 설명을 받아 이해하고 넘어갔습니다. 기능·코드를 쉬운 말로 설명받는 명령([`/explain`](.claude/commands/explain.md))을 만들어 써 왔습니다.

## 사이트 둘러보기

비밀번호는 공개하지 않습니다. 필요하면 관리자에게 받으세요. (대상 대학 NYU Stern)

| 역할 | 이메일 | 쓰임 |
| --- | --- | --- |
| 학생 | student@stern.test | 연세대학교 → Operations Management 편입생 |
| 학생 | yonsei-test@stern.test | 연세대학교 → Operations Management, 성적표 먼저 흐름 테스트용 |
| 심사관(학사처) | registrar@stern.test | 심사 대기열, 교수 배정, 보완 자료 요청, 이의 신청 처리 |
| 학과 교수 | ops.prof@stern.test | Operations Management 과목 판정 |
| 학과 교수 | bns.prof@stern.test | Business and Society 과목 판정 |

기관 관리자 계정은 보안을 위해 적지 않습니다(관리자 2명, 한 명이 잠기면 다른 한 명이 복구). 데모 계정(`demo1234`)은 [내 PC에서 실행](#데모-계정)했을 때와 공개 데모 모드로 직접 올렸을 때만 씁니다.

## 할 수 있는 것

1. **예상 결과 미리 보기 (학생)**: 처음 들어오면 성적표부터 올리고, 성적이 학칙의 인정 최저 성적(데모는 C) 이상인 과목마다 요청이 자동으로 만들어져요. 과목마다 강의계획서(PDF·JPG·PNG)를 올리면 과목마다 인정 추천(직접 인정·선택 인정·불인정·정보 부족)과 원문 근거 구절, 예상 인정 학점·남은 학기·추가 비용을 보여 줍니다. 심사를 요청하기 전에 미리 확인할 수 있습니다.
2. **심사 대기열과 교수 배정 (심사관)**: 정보가 충분한 과목은 학생이 심사를 요청하는 순간 AI가 찾은 대상 과목의 학과 교수에게 자동 배정됩니다. 정보가 부족하거나 대응 과목이 없는 건은 심사 대기열에서 신뢰도·일관성 경보·학과로 걸러 보고 보완 자료를 요청하거나 학과 교수에게 한 번에 배정합니다. 교수가 부재 중이면 대리 심사자에게 넘어갑니다.
3. **근거를 보고 최종 판정 (학과 교수)**: 양쪽 강의계획서 구절을 나란히 보고 승인·수정·반려합니다. 추천과 다르게 판정하면 사유를 고르고, 과거 판정과 다르면 확정 전에 경보가 뜹니다.
4. **보완 자료와 이의 신청**: 정보가 모자라면 학생에게 자료를 요청하고, 학생은 근거 자료를 붙여 이의 신청할 수 있습니다. 재판정도 이전 판정을 지우지 않고 새로 남깁니다.
5. **기관 운영 (관리자)**: 계정·과목 CSV와 기준 강의계획서 등록, 문서 삭제 승인, 운영 통계, 감사 로그, 학사정보시스템 연동(`GET /api/v1/sis/decisions`)을 합니다.
6. **기록과 알림**: 판정 근거 리포트 PDF, 화면·메일 알림, 휴대폰·컴퓨터 브라우저 웹 푸시(설정 시)를 제공합니다. 화면은 한국어·영어로 볼 수 있고, 상단 언어 버튼으로 바꾸면 그 계정의 알림·메일도 같은 언어로 갑니다.

역할별 화면과 메뉴는 아래 [주요 화면](#주요-화면), 화면별 세부는 [화면 명세서](docs/screens/README.md)에 있습니다.

기준 문서: [개발 규칙](CLAUDE.md) · [기획 통합본](docs/spec.md)(페르소나·테스트 명세·기술스택·기능 명세) · [화면 디자인](docs/DESIGN.md) · [화면 명세서](docs/screens/README.md)(화면별 URL·배치·상태) · [구현 현황](docs/traceability.md)(요구사항 → 코드 → 테스트) · [개인정보 처리](docs/privacy.md) · [API 명세](docs/API_Spec.md)(엔드포인트·JSON API) · [ERD](docs/ERD.md)(엔티티·속성·관계) · [미결 사항](docs/open-issues.md)(확정 안 된 규칙·지금 어려운 일) · [실행·배포 자세히](docs/setup.md) · [운영 가이드](docs/operations.md)

## AI가 판정을 추천하는 방식

분석에 쓰는 AI는 Claude(Anthropic)와 GPT(OpenAI) 중에서 고릅니다(`.env`의 `LLM_PROVIDER`). 배포 사이트는 GPT를 씁니다. 어느 쪽이든 아래 단계와 검증 규칙은 같습니다.

1. **추출**: (스캔 PDF·사진은 먼저 AI가 글자로 옮긴 뒤) AI가 강의계획서에서 학습 목표·주차별 주제·교재·선수과목·평가 방식·학점과 학문 분야를 정형 스키마로 뽑습니다. 원문에 없는 값은 비워 둡니다. 같은 문서(내용 해시가 같은 파일)는 다시 분석하지 않고 저장된 결과를 씁니다.
2. **후보 선정**: 추출한 학문 분야로 대상 대학 카탈로그를 학과 단위로 걸러 최대 30개 과목을 후보로 고릅니다. MVP는 임베딩·벡터 검색을 쓰지 않습니다.
3. **개념별 판단**: AI가 후보 과목의 필수 개념마다 실제로 가르쳤는지(다룸/부분/없음/판단 불가), 수준이 같은지 판단하고 양쪽 원문 구절을 인용합니다.
4. **근거 검증**: 인용 구절이 원문에 그대로 있는지 코드로 확인하고, 없으면 버립니다. 원문에 있어도 선수과목·교재·참고문헌 칸에서만 나온 구절이나 "다루지 않음"·"다음 학기"처럼 가르치지 않았다는 문장은 근거로 치지 않습니다. 근거 없이 매긴 커버리지는 40%를 넘지 못합니다. 또 근거 구절이 걸친 주차 수를 세어, 학생 강의계획서는 한 주만 다루는데 기준 과목은 두 주 이상 다루는 개념은 "부분"(최대 50%)까지만 셉니다.
5. **추천 계산**: 개념 커버리지, 추천 등급(직접 인정/선택 인정/불인정, 근거가 모자라면 정보 부족), 신뢰도(상·중·하)를 `backend/services/scoring.py`의 고정 규칙으로 계산합니다. 판정 확률(%)은 MVP에서 계산하지 않습니다. 같은 입력은 저장된 결과를 재사용해 반복 실행해도 결과가 같습니다.

AI가 지어낸 인용(원문에 없어 버린 구절) 비율은 분석마다 기록해 운영 통계의 "AI 근거 품질"에서 프롬프트 버전별로 비교하고, 담당 교수는 판정 화면에서 근거 구절마다 맞음·틀림을 눌러 AI 근거 정확도를 쌓습니다(쌓인 값은 40%·50% 같은 기준값을 데이터로 정하는 데 씁니다).

교수는 승인·수정·반려할 수 있고, 반려하거나 AI 추천과 다르게 판정할 때는 확정 전에 열리는 사유 선택 창에서 선택형 사유(주차 범위 부족·수준 차이·실험·실습 미포함·선수과목 차이·기타)를 고릅니다. '기타'만 메모(최대 500자)가 필수입니다. 같은 출신 과목·같은 대상 과목을 두고 내용이 거의 같은 강의계획서(유사도 80% 이상)에 다른 결과가 나와 있으면 확정 전에 경보를 띄웁니다. 강의계획서가 개편됐으면 이력은 보여 주되 경보는 띄우지 않습니다.

## 주요 화면

| 화면 | 주소 | 누가 | 내용 |
| --- | --- | --- | --- |
| 내 성적표 | `/student/transcript` | 학생 | 처음 로그인하면 이 화면부터: 성적표를 한 번 올리면 AI가 과목 줄을 읽고(이름·학번은 가린 글로 과목을 뽑음, 스캔·사진 파일은 글자를 읽는 단계에서 AI가 원본 이미지를 봄) 학칙 정책의 인정 최저 성적(데모·기존 설정은 C 이상) 이상인 과목마다 편입 요청을 만들어요. 미달 과목은 "성적 기준 미달"로만 보여요. 바꿔 올리면 아직 심사를 요청하지 않은 과목에만 반영 |
| 내 편입 요청(대시보드) | `/student` | 학생 | 성적표 과목마다 만들어진 요청 카드(과목·성적·학점·상태, 학생이 요청을 따로 만들지 않음), 전체 합계(예상 인정 학점·판정 확정·남은 학기, 편입 학점 상한을 넘으면 졸업 학점에 넣을 과목 고르기), 할 일(강의계획서 올리기 N과목·보완 자료 제출 등), 문서 삭제로 종료된 요청은 맨 아래 접힘 |
| 편입 학점 시뮬레이션 리포트 | `/student/requests/{id}` | 학생 | 과목 요청은 그 과목의 강의계획서 한 건을 올리고 AI 결과를 본 뒤 "학사처에 심사 요청". "예상 인정 학점: 낮음~높음 / 이수 학점" 요약, 남은 학기·추가 비용·심사 진행 카드, 과목 필터, 정보 부족 진단과 보완 서류 제출, 심사 진행 4단계 |
| 이의 신청 | `/student/appeals`, `/student/evaluations/{id}/appeal` | 학생 | 이의 신청할 수 있는 과목(그 수가 메뉴 배지로도 보임), 처리 상황(접수·재판정 중·기각 사유·재판정 결과). 작성 화면에서 원 판정 요약을 보며 사유와 근거 자료(PDF·JPG·PNG 최대 3개) 제출 |
| 선배 인정 사례 | `/student/precedents` | 학생 | 기관 동등 과목표를 출신 대학·과목으로 검색 (다른 학생이 받은 판정은 보이지 않음) |
| 심사 대기열 | `/review` | 심사관 | 지표 카드, 이름·과목·출신 대학 검색, 신뢰도·일관성 경보·학과 필터, 커버리지 게이지, 경보 행, 행 선택 후 교수 일괄 배정, SIS CSV 내보내기. 메뉴 "심사 큐" 옆 숫자는 교수 배정이 필요한 과목 수 |
| 이의 신청 처리 | `/review/appeals` | 심사관 | 학생 사유·근거 자료 확인, 받아들이면 재판정 교수 배정, 기각하면 사유 전달. 메뉴 옆 숫자는 처리할 이의 신청 수 |
| 배정된 심사 | `/professor` | 학과 교수 | 판정할 심사(이의 신청 재판정 포함), 최근 판정한 심사 20건(다시 열어 근거 확인), 부재 기간·대리 심사 교수 |
| 판정 화면 | `/professor/evaluations/{id}` | 학과 교수 | 좌우 근거 구절 비교(구절 옆 "원본 N쪽 ↗"은 원본 PDF를 그 쪽으로 새 탭에서 열기, 구절마다 근거 맞음·틀림 표시), 과거 판정 이력, 내부 메모(심사관과 공유, 학생 비공개), 하단 고정 판정 바, 불인정·판정 변경 사유 선택 창 |
| 판정 근거 리포트 | `/evaluations/{id}/report` | 학생·심사관·교수 | 판정자·AI 추천·근거 구절(원본 쪽 번호)·이의 신청 경과. "PDF 내려받기"로 A4 PDF 저장(내부 메모 제외) |
| 계정·과목 관리 | `/admin/data` | 기관 관리자 | ①~④ 순서로 과목 CSV(필수 개념 포함)·과목별 기준 강의계획서(바꾸기·빼기)·계정 CSV·출신 대학(대학별 목록, 쓰지 않는 대학은 지우기), 학칙 정책(인정 최저 성적·편입 학점 상한·졸업 학점·학기당 학점을 학과·입학연도별로, 초안→승인), 학점 단위와 환산 규칙, 비밀번호 초기화(메일 있으면 설정 링크 자동 발송, 없으면 임시 비밀번호 한 번 표시), 졸업·퇴직한 계정 비활성화. 메뉴 옆 숫자는 기준 강의계획서 없는 과목 + 교수가 없는 학과 수 |
| 계정 목록 | `/admin/accounts` | 기관 관리자 | 이메일·역할·상태로 계정 찾기(학생 이름 비공개), 교직원 이름·학과·대리 심사자, 학생 편입 전공·출신 대학 수정, 비밀번호 초기화·비활성화 |
| 교수 배정 | `/admin/assignments` | 기관 관리자 | 판정 전 심사 건의 담당 교수 배정·바꾸기(학과 자동 배정 또는 교수 지정). AI 추천·커버리지·근거는 보이지 않음 |
| 관리자 콘솔 | `/admin/stats` | 기관 관리자 | AI 추천 수용률, 개인정보 보호·SIS 연동 상태, 학과별 처리 지표, AI 근거 품질(프롬프트 버전별 지어낸 인용 비율·교수 확인 정확도), 최근 감사 로그, 데이터 보존 및 파기 정책 (심사관은 `/review/stats`에서 감사 로그를 뺀 운영 통계) |

- 상단 메뉴는 역할마다 다르고, 메뉴 옆 숫자로 각자 처리할 일을 알려 줍니다(0이면 숨김). 주황은 처리할 일, 파랑은 새 결과, 회색은 참고 개수입니다.

  | 역할 | 메뉴 | 숫자 배지 |
  | --- | --- | --- |
  | 학생 | 내 편입 요청 · 성적표 · 이의 신청 · 인정 사례 | 내 편입 요청: 채워야 할 서류 수(주황)·새 판정 결과 수(파랑) / 이의 신청: 신청할 수 있는 과목 수(회색)·새 이의 신청 결과 수(파랑). 새 판정 결과는 그 과목 결과를 열면, 새 이의 신청 결과는 이의 신청 화면을 열면 사라짐 |
  | 심사관 | 심사 큐 · 이의 신청 · 삭제 요청 · 동등 과목표 · 통계 · CSV 내보내기 | 심사 큐: 교수 배정이 필요한 과목 수 / 이의 신청: 처리할 건수 / 삭제 요청: 처리할 건수 |
  | 학과 교수 | 배정된 심사 | 판정할 건수(이의 신청 재판정 포함) |
  | 기관 관리자 | 운영 통계 · 계정·과목 · 계정 목록 · 교수 배정 · 삭제 승인 · 학사정보 연동 · 감사 로그 | 계정·과목: 준비가 필요한 항목 수(기준 강의계획서 없는 과목·교수가 없는 학과) / 계정 목록: 확인이 필요한 계정 수(로그인 실패로 비밀번호가 초기화된 계정, 출신 대학·편입 전공이 빈 학생) / 교수 배정: 교수 배정이 필요한 과목 수 / 삭제 승인: 승인할 건수 |

  알림·판정 근거 리포트·비밀번호 변경처럼 여러 역할이 함께 쓰는 화면에도 같은 메뉴와 숫자가 나오고, 모바일에서는 햄버거 메뉴 안에 들어갑니다. 첫 로그인 비밀번호 변경 중과 오류 화면에는 역할 메뉴가 없습니다.
- 화면은 [DESIGN.md](docs/DESIGN.md)(단일 Action Blue, 1px 헤어라인, 그림자 없음)를 따릅니다. 폭은 기본 1280px이고, 정보가 많은 심사 대기열과 원문 대조 화면만 1440px입니다.
- 화면에 판정 확률(%)은 없습니다. 커버리지, 3단계 추천, 신뢰도만 보여 줍니다. 교수·관리자 화면에는 학생 이름이 나오지 않습니다.
- 모든 화면 아래에 "본 시스템의 AI 분석 결과는 심사 참고용 근거 자료이며, 최종 학점 인정 여부는 해당 학과 교수의 승인으로 확정됩니다."라는 Human-in-the-Loop 고지가 있습니다.

## 실행

### Docker로 한 번에 (내 컴퓨터에서만 접속)

사전 설치: [Docker Desktop](https://www.docker.com/products/docker-desktop/), Git

Docker Desktop을 먼저 실행하고, 창 왼쪽 아래에 **Engine running**이 보일 때까지 기다린 뒤 터미널(Windows는 PowerShell)에서 한 줄씩 실행합니다.

```bash
git clone https://github.com/Hyeonwoo01/CreditBridge_AI.git
cd CreditBridge_AI
cp .env.example .env                      # (선택) Windows PowerShell: copy .env.example .env
# .env에 ANTHROPIC_API_KEY만 넣으면 실제 AI 분석(CLAUDE_MODEL은 예시 값이 들어 있음. GPT는 LLM_PROVIDER=openai, OPENAI_API_KEY, OPENAI_MODEL). .env가 없어도 실행은 되고, AI 분석만 "AI 분석 설정(API 키)이 아직 없어 분석하지 못했어요"로 실패 표시
docker compose up -d --build              # 프론트엔드·백엔드·DB·작업 큐·파일 저장소를 한 번에
```

처음에는 빌드에 몇 분 걸려요. 브라우저에서 http://localhost:8000 을 열고 아래 [데모 계정](#데모-계정)으로 로그인합니다(비밀번호 `demo1234`). 끄기는 `docker compose down`이에요.

서비스 구성, 내 이메일로 계정 만들기, 막힐 때, AWS 배포, 개발용 실행(uv)은 [docs/setup.md](docs/setup.md)에 있어요.

### 데모 계정

내 PC에서 실행(Docker 또는 uv)하면 아래 계정이 미리 만들어져 있습니다. **비밀번호는 모두 `demo1234`** 입니다.

- 배포 사이트(https://creditbridge-hw.duckdns.org)에는 이 계정들이 없습니다. 운영에서는 `SEED_DEMO=false`로 데모 계정을 만들지 않고, 기관 관리자가 [계정 CSV](docs/setup.md#내-이메일로-계정-만들기)로 계정을 만들어 줍니다.
- [공개 데모](docs/setup.md#예시용-공개-데모로-올리기-render-무료)를 직접 올리면 로그인 화면의 역할 버튼을 누르면 비밀번호 없이 바로 들어갑니다.

| 역할 | 이메일 | 둘러볼 것 |
| --- | --- | --- |
| 학생 | jiwon@student.example | 처음 로그인하면 성적표부터: `scripts/demo_data/transcript.pdf`를 올리면 C 이상 6과목 요청이 생김(C프로그래밍은 D라 제외) → 과목마다 강의계획서 올리기·심사 요청·이의 신청 |
| 학생(선배) | senior@student.example | 작년에 선형대수가 직접 인정된 이력이 있는 학생(일관성 경보 시연용). 로그인하면 이 계정도 성적표부터 올려야 함 |
| 심사관 | rachel@msu.example | 심사 대기열, 교수 배정, 보완 자료 요청 |
| 수학과 교수 | dkim@msu.example, lchen@msu.example | 미적분학·선형대수 판정 |
| CS 교수 | oali@msu.example, spark@msu.example | 자료구조 판정 (C프로그래밍은 데모 성적표에서 D라 요청이 생기지 않음) |
| 물리·화학·영어·역사 교수 | mbrown@msu.example, ewong@msu.example, alopez@msu.example, jreed@msu.example, twhite@msu.example | 해당 학과 과목 판정 |
| 관리자 | admin@msu.example | 계정·과목 관리, 삭제 승인, 운영 통계, 감사 로그 |

`retired@msu.example`은 작년 판정을 내린 퇴임 교수 기록용 계정이라 둘러볼 때는 쓰지 않습니다. 비밀번호를 바꿨거나 잊었으면 `docker compose down -v` 후 다시 `up -d --build` 하면 처음 상태로 돌아갑니다(올린 데이터도 지워짐).

로그인하면 역할별 첫 화면으로 갑니다: 학생은 내 편입 요청 대시보드(성적표를 아직 안 올렸으면 내 성적표 화면, 과목 카드를 누르면 시뮬레이션 리포트), 심사관은 심사 대기열, 교수(예: mbrown)는 배정된 심사(메뉴 옆 숫자는 판정할 건수), 관리자는 관리자 콘솔입니다.

`scripts/demo_data/`에 페르소나의 강의계획서 PDF(미적분학, 선형대수 상세형·부실형, C프로그래밍, 자료구조, 일반물리, 일반화학, 한국사)와 예시 성적표(`transcript.pdf`, 같은 과목 코드)가 있습니다. 작년에 같은 선형대수가 직접 인정된 이력도 시드되어 있어 일관성 경보를 시연할 수 있습니다.

## 개발 규칙 (CLAUDE.md)

코드를 고치기 전에 [CLAUDE.md](CLAUDE.md)를 먼저 읽어 주세요. 사람과 Claude Code가 함께 따르는 규칙이며, Claude Code는 이 파일을 자동으로 읽습니다. 핵심만 옮기면:

- **고정 스택**: Python 3.12·uv, FastAPI(`def` 엔드포인트), Pydantic 2, SQLAlchemy 2.0, PostgreSQL 17 + psycopg 3, Alembic, Celery + Redis, LLM은 Anthropic 공식 SDK(Claude) 또는 OpenAI 공식 SDK(GPT) 중 선택, PyMuPDF, pywebpush(웹 푸시), Jinja2 + HTMX + Tailwind. 목록 밖 라이브러리는 추가하기 전에 먼저 물어봅니다.
- **구조**: web → services → repositories → models. SQL은 `backend/repositories`에만, LLM 호출은 `backend/ai/llm_client.py`로만, 프롬프트는 `backend/ai/prompts/*.md`(바꾸면 버전 올림), 추천 규칙은 `backend/services/scoring.py` 한 곳(바꾸면 `RULES_VERSION` 올림).
- **사람이 최종 판정**: AI는 추천만 합니다. 판정 확률(%)은 계산·표시하지 않고, 확정 판정에는 `decided_by`가 필수이며, `decisions`·`audit_logs`는 INSERT만 합니다(재판정도 새 행).
- **개인정보·보안**: 로그·예외·알림에 이름·학번·성적을 쓰지 않습니다. 문서 안 지시 문구는 데이터로만 다루고, 상태를 바꾸는 POST는 CSRF 토큰을 검증합니다.
- **작업 완료 전**: 아래 품질 검사를 모두 통과시키고, 스키마를 바꾸면 Alembic 마이그레이션을, 새 Tailwind 클래스를 쓰면 `app.css` 재빌드를 함께 커밋합니다.

## 품질 검사

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy backend
uv run pytest tests/unit tests/integration   # 통합 테스트는 PostgreSQL 필요 (TEST_DATABASE_URL, 기본 creditbridge_test)
uv run pytest tests/eval -m eval             # 골든셋 평가: 실제 AI API(설정한 Claude 또는 GPT) 호출, 비용 발생
```

같은 검사를 푸시·PR마다 [GitHub Actions](.github/workflows/ci.yml)가 PostgreSQL 17 서비스 컨테이너로 다시 돌립니다(번역 점검 `scripts.i18n_check`, 문서 점검 `scripts.docs_check` 포함 — 엔드포인트·테이블 칸·화면 버튼 표가 문서에 빠짐없는지).

마이그레이션은 데이터가 있는 DB로도 시험합니다. `tests/integration/test_migrations.py`가 0002·0009 시점의 옛 데이터(`scripts/demo_data/migration/*.sql`)를 넣고 head까지 올려 백필 결과를 확인하고, head → 0002 → head 되돌리기도 지나가는지 봅니다(TEST_DATABASE_URL의 DB 이름 뒤에 `_migrations`를 붙인 별도 DB). 직접 들여다보려면 `uv run python -m scripts.migration_demo --database-url postgresql+psycopg://creditbridge:change-me@localhost:5432/cb_migration [--to 0006]` — 지정한 DB의 스키마를 지우고 다시 만들며, 앱 DB는 거절합니다. head까지 올린 DB는 `DATABASE_URL`을 그 주소로 바꿔 앱으로 열 수 있습니다(예: `admin@legacy.example`, `multi@student.example`, 비밀번호 `demo1234`).

테스트에서는 AI·S3를 대역(`tests/fakes.py`)으로 바꿉니다. 대역 AI는 일부러 원문에 없는 구절을 섞어 내보내고, 테스트는 그 구절이 저장되지 않는지 확인합니다.

## 구조

주요 폴더와 파일만 적었습니다.

```
backend/         ← 백엔드 (Python, import 이름도 backend)
  main.py        FastAPI 앱, /static 마운트(frontend/static)
  config.py      환경변수(Settings) · i18n.py · locales/(영어 번역) · db/(세션·공통 타입) · schemas/(AI 출력 스키마)
  ai/            llm_client.py(SDK 단일 진입점) · prompts/*.md · extraction · candidates · matching · evidence · injection · demo_llm(예시 AI)
  documents/     PyMuPDF 텍스트 추출(PDF·JPG·PNG, 스캔 페이지·이미지는 AI 전사), S3 저장
  services/      analysis(파이프라인) · scoring(추천 규칙) · student · review(심사 대기열) · decisions(판정·경보)
                 materials · appeals(이의 신청·근거 자료) · privacy · notifications · sis · equivalencies · precedents(학생 인정 사례)
                 stats(통계·관리자 콘솔) · views(화면 조회·학생 대시보드·역할별 메뉴 배지 nav_badges)
                 push(웹 푸시 구독·발송) · calibration(추천 기준값 보정 계산)
                 institution_data(계정·과목 CSV, 기준 강의계획서, 출신 대학, 학칙 정책·환산 규칙 관리, 첫 관리자) · policy(학칙 정책 엔진) · credits(학점 단위·환산) · csv_import(CSV 공통)
                 accounts · auth · audit · notes(내부 메모) · originals(원본 열람) · reminders(기한 알림) · versions(버전 비교)
                 evidence_feedback(교수 근거 맞음·틀림, AI 근거 품질 지표) · evidence_status(증거 출처·진위·적용 학기)
                 case_state(심사 상태·동시 수정 방지)
  repositories/  SQL은 여기만
  models/        SQLAlchemy 2.0, 테이블당 1파일
  workers/       Celery 작업
  security/      세션·권한·CSRF·개인정보 마스킹·악성코드 검사(ClamAV, 기본 꺼짐)
  web/           라우트(routes/), JSON API(api/), 템플릿 렌더링(templating.py: frontend/templates 사용), 역할별 메뉴 숫자 배지(nav.py)
frontend/        ← 프론트엔드 (서버가 그려 보내는 화면 파일)
  templates/     Jinja2 + HTMX 템플릿: base · login · account · student · review · professor · admin · partials · notifications · stats · report
  static/        css/app.css(빌드 결과) · js/app.js · img/(로고·아이콘) · samples/(CSV 예시)
  tailwind/      input.css (DESIGN.md 토큰, Tailwind 4 입력)
alembic/         마이그레이션 (PostgreSQL 17, 기준점 0001에 이전 MariaDB 마이그레이션을 합침)
db/              init.sql(스키마, alembic --sql로 생성) · data.sql(데모 초기 데이터, pg_dump로 생성) — scripts/export_db_sql.sh로 다시 만듦
scripts/         start.sh · build_css.sh · create_admin(첫 관리자) · seed_demo · create_bucket · backfill_page_offsets(원본 쪽 번호 채우기) · i18n_check(영어 번역 점검) · docs_check(API 명세·ERD·화면 명세 점검) · export_db_sql(db/*.sql 다시 만들기) · generate_vapid_keys(웹 푸시 키) · calibrate_scoring(추천 기준값 보정 보고서) · migration_demo(옛 데이터로 마이그레이션 시험) · demo_data/ · demo_scenario·make_demo_pdfs(공개 데모 데이터)
tests/           unit · integration(PostgreSQL) · eval(골든셋) · fixtures/(학점 계산·문서 추출 회귀 기대값, 인젝션 공격 문구 모음)
```

백엔드와 프론트엔드는 폴더만 나뉘어 있고 하나의 앱으로 함께 실행됩니다. FastAPI가 `frontend/templates`로 HTML을 그려 보내고 `frontend/static`을 `/static`으로 내보냅니다.

화면 CSS는 `frontend/tailwind/input.css`(DESIGN.md 토큰)에서 Tailwind standalone CLI로 빌드합니다(`scripts/build_css.sh`). 빌드된 `frontend/static/css/app.css`가 커밋되어 있어 CLI 없이도 실행됩니다. 템플릿에 새 Tailwind 클래스를 쓰면 `scripts/build_css.sh`로 다시 빌드해 함께 커밋하세요.

## 운영

실제 기관 데이터로 시작하는 순서(첫 관리자·과목·기준 강의계획서·계정 CSV)와 운영할 때 확인할 것(보안·환경 변수·알림·임시 기준값)은 [docs/operations.md](docs/operations.md)에 있어요. AWS에 올리는 순서는 [docs/deploy-aws.md](docs/deploy-aws.md)에 있어요.
