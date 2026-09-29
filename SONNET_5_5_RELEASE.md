# Claude Sonnet 5.5 공식 출시 조사 및 검증 리포트 (Zero-Hallucination Verified)

> **문서 목적**: 2026년 9월 28일 출시된 Anthropic의 **Claude Sonnet 5.5**(`claude-sonnet-5-5`)의 공식 사양, 벤치마크, API 제약사항, 실무 가이드라인 및 강의 사이트 반영·실검증 결과를 객관적 사실에 기반하여 기록합니다.

---

## 1. 모델 핵심 스펙 및 공식 정보 (교차 검증)

| 항목 | 공식 실측 및 사양 | 비고 및 출처 |
| :--- | :--- | :--- |
| **공식 모델명** | **Claude Sonnet 5.5** | Anthropic Newsroom (2026-09-28) |
| **API Model ID** | **`claude-sonnet-5-5`** | Claude Platform API Docs, AWS Bedrock, GCP Vertex AI, MS Foundry |
| **출시일자** | **2026년 9월 28일** | Opus 5.5(9월 22일)에 이은 Claude 5.5 패밀리 2번째 모델 |
| **컨텍스트 창** | **1,000,000 토큰 (1M)** | 대규모 코드베이스 및 긴 세션 지원 |
| **최대 출력 토큰** | **128,000 토큰 (128K)** | Sonnet 5 및 Opus 5.5와 동일한 최대 출력 창 |
| **학습 지식 컷오프** | **2026년 6월** | Claude Sonnet 5.5 System Card |
| **토큰 기본 요율** | 입력 **$2.00 / 1M 토큰**, 출력 **$10.00 / 1M 토큰** | 정규 요율은 기존 Sonnet 5와 동일 |
| **프롬프트 캐싱** | 캐시 생성(Write) **$2.50 / 1M**, 캐시 읽기(Read) **$0.20 / 1M** | 캐시 적중 시 입력 비용 90% 절감 ($0.20/M) |
| **작업당 실효 비용** | 작업 완료당 **최대 30% 비용 절감** | 향상된 지능과 간결성(conciseness)으로 소모 토큰 수 감소 |
| **출력 생성 속도** | Sonnet 5 대비 **30% 이상 가속 (30%+ Faster)** | 대화형 코딩 및 고속 에이전틱 루프 최적화 |
| **기본 제공 플랫폼** | Claude API, Bedrock, Vertex AI, Microsoft Foundry, GitHub Copilot, **Claude.ai 무료 티어 기본 모델** | 웹/모바일 claude.ai 기본 탑재 |

---

## 2. 벤치마크 및 지능 평가 실측치

1. **에이전틱 터미널 코딩 (Terminal-Bench 4.0)**:
   - **Sonnet 5.5: 70.6%**
   - Sonnet 5 (이전 세대): **10.3%**
   - *평가 결과*: 7배에 가까운 비약적 성공률 향상을 기록하며 Artificial Analysis 리더보드 1위 달성. 복잡한 CLI 명령어 조합, 자체 디버깅, 환경 복구 능력이 플래그십 수준으로 격상됨.
2. **실무 경제/지식 작업 (GDPval-AA v2.1)**:
   - **Sonnet 5.5: 1,844 Elo**
   - Opus 5.5 (플래그십): **1,846 Elo**
   - *평가 결과*: 분석 보고서, 슬라이드, 문서 작성 등 일상적인 지식 작업 영역에서 플래그십 모델과 2점 차이의 대등한 성과 발휘.
3. **시각 멀티모달 추론**:
   - 텍스트 가이드나 사전 치트 없이 **순수 스크린샷 픽셀 입력만으로 포켓몬 레드(Pokémon Red) 게임 완결**.
   - 다이어그램, UI 디자인 시안, 터미널 캡처 판독 정밀도 강화.

---

## 3. 핵심 API 변경사항 및 브레이킹 체인지 (개발자 필독)

Sonnet 5에서 Sonnet 5.5(`claude-sonnet-5-5`)로 마이그레이션할 때 주의해야 할 브레이킹 체인지는 다음과 같습니다:

1. **사고(Thinking) 끄기 설정 방식 변경**:
   - `thinking: {"type": "disabled"}` 설정은 더 이상 유효하지 않거나 거부됩니다.
   - `high` 이하 effort 설정에서 도구 호출 간에 사고를 끄려면 **`thinking: {"type": "between_tools"}`**를 사용해야 합니다.
2. **강제 도구 선택(Forced tool_choice) 금지**:
   - `tool_choice`에 `any` 또는 특정 `tool` 이름을 강제 지정하면 **HTTP 400 Bad Request** 에러를 반환합니다.
3. **구형 컴퓨터 사용 도구 배제**:
   - 이전 세대의 `computer_20251124` 버전 도구는 Sonnet 5.5 API 요청 시 거부됩니다.
4. **어드바이저 모델 계층 강제**:
   - Sonnet 5.5 메인 세션에 구형 모델(Sonnet 5, Opus 4.8, Opus 4.7)을 `/advisor`로 지정하는 역방향 계층 구조는 시스템에서 거부됩니다.
5. **Thinking 블록의 암호학적 계정 격리**:
   - Sonnet 5.5가 생성한 사고 블록은 생성 계정에 암호학적으로 귀속됩니다. 타 계정이 해당 블록을 전송하면 API가 이를 자동으로 드롭합니다.

---

## 4. Claude Sonnet 5.5 공식 프롬프트 엔지니어링 10대 패턴 (공식 가이드 검증)

Anthropic 공식 문서 [**Prompting Claude Sonnet 5.5**](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5)에서 제시된 10대 실전 패턴입니다:

1. **Effort 재조정 및 max_tokens**: API 기본값은 `high`. 에이전틱 코딩은 `medium`에서 시작해 난도에 따라 `high`로 상향. 코딩 시 `max_tokens`는 thinking을 포함하므로 최대치인 `128000` 설정 권장. `output_config.effort`(beta)로 턴별 제어 시 프롬프트 캐시 보존.
2. **자율성과 작업 범위 제어**: `low`/`medium`의 조기 중단 방지 프롬프트 주입. `xhigh`/`max`에서 자체 리뷰/서브에이전트 남발 방지 프롬프트 주입(세션 비용 30% 절감). 아이디어 요청 시 앱 제작 방지 지시.
3. **between_tools 제약**: `high` 이하 effort에서만 유효 (`xhigh`/`max`는 400 에러). "생각하지 말라"는 지시는 XML 태그 유출을 부르므로 금지. 중간 사고 블록은 원본 그대로 전송.
4. **정형 JSON 추론**: 구조화 출력(structured outputs) 시 본문은 JSON만 나오므로 추론은 thinking에서 진행됨. "Think the problem through before you answer." 주입 권장. `stop_reason: "max_tokens"`는 실패 처리 후 재시도. 비정형 시 응답의 마지막 JSON 블록 파싱.
5. **진행 상황 실시간 업데이트**: `display: "updates"` 헤더 지원. 5회 이상 연속 침묵 시 하네스 일회성 턴 스코프 리마인더 주입.
6. **지식 및 검색 도구 활용**: "도구 최소화" 지침 삭제. 최신 세부사항(허용 여부, 규정, 요금)은 학습 지식 대신 검색 도구 강제.
7. **미드턴 메시지와 간접 인젝션 방어**: 절대 `tool_result` 블록 내부에 사용자 텍스트 삽입 금지 (간접 인젝션으로 오탐). 사용자 입력은 별도 `text` 블록으로 추가.
8. **코딩 실검증 강제**: `low` effort에서 의존성 핑계로 테스트를 건너뛰는 행위 차단 프롬프트 주입.
9. **관용적 도구 호출 처리**: `bash` vs `Bash` 등 대소문자 차이는 허용하거나 `is_error: true`로 기대 규격 회신해 자체 교정 유도.
10. **복합 시각 입력 & 5대 거부 카테고리**: 조밀한 차트/도면은 crop/zoom 도구 제공이 효과적. 거부 시 `stop_details.category` 5종(`cyber`, `bio`, `frontier_llm`, `reasoning_extraction`, `general_harms`) 대응.

---

## 5. Claude Code 실무 가이드라인

- **기본 추천**: **일상적인 기능 개발, 빠른 인터랙티브 코딩, 고속 에이전틱 작업**에는 **Sonnet 5.5**를 기본 모델로 권장 (`/model sonnet` 또는 `/model sonnet-5-5`).
- **Opus 5.5와의 역할 분담**:
  - **Sonnet 5.5**: 30% 빠른 반응 속도, 초고속 버그 수정, 일상 업무, 작업당 비용 30% 절감.
  - **Opus 5.5**: 대규모 아키텍처 리팩터, 복잡한 다중 파일 변경, 긴 세션 무인 자율 실행(CLAUDE.md 스톱 규칙, TASKS.md 연계).
  - **Fable 5.1**: 최고 난도 수학/하드웨어 증명, 극단적 엣지케이스 보안 감사.
  - **Haiku 4.5**: 코드베이스 단순 분류, 초고속 경량 서브에이전트.

---

## 6. 강의 사이트 반영 및 5대 필수 검증 실측 증거

### 1) 파일 수정 내역
- `content/03-models.md`: Sonnet 5.5 공식 사양, 벤치마크, 5대 브레이킹 체인지, 의사결정 다이어그램 반영.
- `content/14-prompt-guide.md`: Anthropic 공식 문서("Prompting Claude Sonnet 5.5") 10대 패턴(추론 강도 재조정, 자율성 제어, between_tools 제약, JSON 추론, 간접 인젝션 방어, 실검증 강제 등) 3부 신설, Fable 5.1(4부), 마이그레이션(5부) 재배치 및 요약 반영.
- `content/18-references.md`: `Prompting Claude Sonnet 5.5` 공식 URL(`https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5`) 1차 출처 표 추가.
- `build_course.py`: 6개 모델 비용 계산기(`const M`), 1M 컨텍스트 예산(`const WIN`), 프롬프트 튜너 옵션 연동.
- `tools/regress.mjs`: 계산기 모델 비교 행 검증 로직 동기화(6개 모델).

### 2) 빌드 및 회귀 테스트 실측치 (로컬)
- **명령**: `python3 build_course.py && node tools/prerender.mjs && node tools/regress.mjs`
- **결과**: **32 / 32 전건 PASS 통과**
- **CDP 실측**: LayoutObjects 1568 (기준 ≤ 5000 충족)

### 3) 라이브 배포 및 교차 검증 실측치
- **배포 URL**: `https://claude-code-tutorial-ko.vercel.app` (Git Commit `cfdca26`)
- **바이트 레벨 비교**:
  ```bash
  curl -s https://claude-code-tutorial-ko.vercel.app | cmp - index.html
  # 종료 코드 0 (0 바이트 차이, 완벽 일치)
  ```
  - 로컬 파일 크기: **1,061,642 바이트**
  - 라이브 Content-Length: **1,061,642 바이트**
- **라이브 브라우저 회귀 테스트**:
  ```bash
  node tools/regress.mjs --url https://claude-code-tutorial-ko.vercel.app
  # 32 / 32 전건 PASS 통과 (LayoutObjects 1574)
  ```
- **보안 헤더 실측치**:
  - `strict-transport-security: max-age=63072000; includeSubDomains; preload`
  - `x-content-type-options: nosniff`
  - `x-frame-options: SAMEORIGIN`
  - `x-xss-protection: 1; mode=block`
  - `referrer-policy: strict-origin-when-cross-origin`
  - `permissions-policy: camera=(), microphone=(), geolocation=(), payment=()`
  - 런타임 외부 네트워크 요청: **0건**
- **반응형 뷰포트 3종 가로 오버플로우**: 1280px (0px), 900px (0px), 390px (0px).
