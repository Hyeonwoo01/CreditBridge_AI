# 개인정보 처리 (FR-13, NF-01~NF-03)

CreditBridge AI가 학생 문서를 어떻게 저장·전송·삭제하는지 정리한다. 기관 도입 심사(FERPA) 때 이 문서를 근거로 설명한다.

## 무엇을 어디에 저장하나

| 데이터 | 저장 위치 | 비고 |
| --- | --- | --- |
| 원본 강의계획서·성적표 파일 | 객체 스토리지(S3 호환) | 운영은 `S3_SERVER_SIDE_ENCRYPTION=AES256` 또는 `aws:kms`로 저장 암호화. DB에는 파일 키만 |
| 강의계획서 추출 텍스트·구조화 결과 | `syllabi.raw_text`, `syllabi.extracted_json` | 강의 내용이며 학생 개인정보는 아님 |
| 성적표 과목·학점·성적 | `transcript_entries` | 이름·학번·생년월일은 저장하지 않고, 이름은 마스킹 값(`L** J****`)만 |
| AI 분석 결과·근거 구절 | `course_evaluations`, `evidence_spans` | 강의계획서 구절과 원문 위치 |
| 교수 판정·감사 로그 | `decisions`, `audit_logs` | 추가 전용. 사용자 id와 행위만 기록하고 이름·학번·성적은 넣지 않음 |

## 모델 입력과 로그

- 성적표는 `app/security/masking.py`가 이름·학번·생년월일을 가린 뒤에만 Claude에 보낸다 (NF-01, `tests/unit/test_injection_and_masking.py`, `test_transcript_is_masked_before_llm_and_linked`).
- 애플리케이션 로그와 예외 메시지에는 이름·학번·성적을 쓰지 않는다. 로그에는 id와 오류 종류만 남긴다.
- 전송 구간은 TLS로 보호한다. 운영 배포 시 리버스 프록시에서 TLS 1.2 이상만 허용한다 (NF-02).

## 모델 학습에 쓰지 않음 (NF-03)

- CreditBridge AI는 학생 문서를 학습용 데이터로 따로 모으거나 내보내는 경로가 없다. 저장된 데이터는 해당 심사 건 처리와 감사에만 쓴다.
- Claude 호출은 Anthropic API(상용 이용 약관)로 한다. Anthropic은 상용 API로 받은 입력·출력을 기본적으로 모델 학습에 쓰지 않는다. 계약 전 최신 상용 약관과 데이터 보존 기간을 확인해 기관에 함께 제출한다.

## 삭제 요청

- 학생은 요청 화면의 "내 문서 삭제 요청"으로 본인 요청의 원본 파일(강의계획서·성적표)과 추출 텍스트, 성적표 과목 목록, 청크를 즉시 지울 수 있다 (`services/student.py::delete_documents`, `test_privacy_delete_removes_files_and_text`).
- 삭제한 문서는 같은 문서 결과 재사용(content_hash)의 출처에서도 빠진다.
- 교수 판정과 감사 로그는 학사 기록이므로 남는다. 여기에는 판정 결과와 판정 당시 AI 추천 요약만 있고 원본 문서는 없다.
- 기관 관리자의 삭제 승인 절차와 삭제 기한 관리 화면은 아직 없다 (traceability 참고).
