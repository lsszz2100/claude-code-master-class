스킬(Skill)은 Claude의 능력을 확장하는 **재사용 가능한 지식·절차 묶음**입니다. `SKILL.md` 파일에 지시를 적어 두면 Claude가 자기 도구상자에 추가하고, 관련될 때 스스로 불러오거나 `/스킬이름`으로 직접 호출할 수 있습니다.

**언제 스킬을 만드나?** 같은 지시·체크리스트·다단계 절차를 채팅에 반복해서 붙여 넣고 있을 때, 또는 `CLAUDE.md`의 한 섹션이 "사실"이 아니라 "절차"로 커졌을 때입니다.

> **스킬의 결정적 장점 — 온디맨드 로딩**: `CLAUDE.md`는 매 세션 전체가 로드되지만, **스킬 본문은 실제로 쓰일 때만 로드**됩니다. 그래서 긴 참조 자료도 필요하기 전까진 컨텍스트 비용이 거의 0입니다. "가끔만 필요한 도메인 지식·워크플로"는 CLAUDE.md가 아니라 스킬에 두세요.

스킬은 [Agent Skills](https://agentskills.io) 오픈 표준을 따라 여러 AI 도구에서 호환됩니다.

---

## 첫 스킬 만들기

스킬은 **디렉터리 + `SKILL.md`**입니다. 디렉터리 이름이 곧 명령어(`/`)가 됩니다.

```bash
mkdir -p ~/.claude/skills/summarize-changes
```

`~/.claude/skills/summarize-changes/SKILL.md`:

```markdown
---
description: 커밋되지 않은 변경을 요약하고 위험 요소를 표시. 사용자가 무엇이 바뀌었는지 묻거나, 커밋 메시지·diff 리뷰를 원할 때 사용.
---

## 현재 변경사항
!`git diff HEAD`

## 지시
위 변경을 2~3개 불릿으로 요약한 뒤, 누락된 에러 처리·하드코딩·수정이 필요한
테스트 같은 위험을 나열하라. diff가 비어 있으면 변경 없음이라고 답하라.
```

`` !`git diff HEAD` ``는 **동적 컨텍스트 주입** — Claude가 스킬을 보기 전에 명령이 실행되어 실제 diff가 인라인됩니다. 이제 "뭐가 바뀌었어?"라고 물으면 자동으로, `/summarize-changes`로는 직접 호출됩니다.

---

## 어디에 두는가

| 위치 | 경로 | 적용 범위 |
| --- | --- | --- |
| 엔터프라이즈 | 관리 설정 | 조직 전체 |
| 개인 | `~/.claude/skills/<name>/SKILL.md` | 내 모든 프로젝트 |
| 프로젝트 | `.claude/skills/<name>/SKILL.md` | 이 프로젝트만 |
| 플러그인 | `<plugin>/skills/<name>/SKILL.md` | 플러그인 활성 시 |

이름이 겹치면 엔터프라이즈 > 개인 > 프로젝트 순으로 이깁니다. 스킬 디렉터리는 **라이브 변경 감지** — 세션 중 추가·수정·삭제가 재시작 없이 반영됩니다(최상위 디렉터리를 새로 만든 경우만 재시작).

---

## 프론트매터 레퍼런스

`description`만 권장 필수입니다. 자주 쓰는 필드:

| 필드 | 설명 |
| --- | --- |
| `name` | 목록에 표시될 이름(기본: 디렉터리명) |
| `description` | **무엇을·언제** 쓰는지. Claude의 자동 호출 판단 근거. 앞부분에 핵심 용례를 두세요(목록에서 1,536자로 잘림) |
| `disable-model-invocation` | `true`면 Claude 자동 호출 차단, 사용자만 `/name`으로 |
| `user-invocable` | `false`면 `/` 메뉴에서 숨김(Claude만 사용) |
| `allowed-tools` | 호출 턴 동안 승인 없이 쓸 도구. 다음 메시지에 해제 |
| `disallowed-tools` | 스킬 활성 중 제거할 도구 |
| `model` / `effort` | 스킬 활성 중 모델·추론강도 오버라이드 |
| `context` | `fork` 설정 시 격리된 서브에이전트에서 실행 |
| `agent` | `context: fork`일 때 쓸 서브에이전트 타입 |
| `paths` | 매칭 파일을 다룰 때만 자동 활성화(글롭) |

### 누가 호출하는가 통제

```markdown
---
name: deploy
description: 애플리케이션을 프로덕션에 배포
disable-model-invocation: true
---
```

- `disable-model-invocation: true` → **사용자만** 호출. `/commit`·`/deploy`처럼 부작용이 있거나 타이밍을 통제하고 싶은 워크플로에.
- `user-invocable: false` → **Claude만** 호출. `/`로 실행할 의미가 없는 배경 지식(예: `legacy-system-context`)에.

### 도구 사전 승인

```markdown
---
name: commit
description: 현재 변경을 스테이징하고 커밋
disable-model-invocation: true
allowed-tools: Bash(git add *) Bash(git commit *) Bash(git status *)
---
```

`allowed-tools`에 나열된 도구는 스킬을 호출한 턴 동안 **권한 프롬프트 없이** 실행됩니다(다음 메시지에 해제).

---

## 지원 파일과 점진적 공개

스킬 디렉터리에는 여러 파일을 둘 수 있습니다. `SKILL.md`는 핵심만 담고, 상세 자료는 **필요할 때만** 로드하게 하세요.

```text
my-skill/
├── SKILL.md          # 필수 — 개요·내비게이션
├── reference.md      # 상세 API(필요 시 로드)
├── examples.md       # 예시(필요 시 로드)
└── scripts/
    └── helper.py     # 실행용 스크립트(로드 아님)
```

`SKILL.md`에서 지원 파일을 참조해 Claude가 무엇이 어디 있는지 알게 하세요.

> **팁**: `SKILL.md`는 500줄 이하로. 본문은 한번 로드되면 세션 내내 컨텍스트에 남아 매 턴 토큰 비용이 되므로, "왜·어떻게"를 늘어놓기보다 "무엇을 하라"를 간결히 적으세요.

### 스크립트 번들링

스킬은 어떤 언어의 스크립트든 번들해 실행할 수 있어, 단일 프롬프트로 불가능한 능력을 줍니다(데이터 시각화, 의존성 그래프, 커버리지 리포트 등). `${CLAUDE_SKILL_DIR}` 변수로 설치 위치와 무관하게 스크립트를 참조하세요.

```markdown
---
name: render-chart
description: CSV로 차트 렌더링
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/render.sh *)
---

`${CLAUDE_SKILL_DIR}/scripts/render.sh <csv-file>` 를 실행해 차트를 렌더링하라.
```

---

## 서브에이전트에서 실행 (`context: fork`)

`context: fork`를 넣으면 스킬이 **격리된 서브에이전트**에서 실행됩니다. 스킬 본문이 그 서브에이전트의 프롬프트가 되고, 메인 대화 히스토리에는 접근하지 않습니다.

```markdown
---
name: deep-research
description: 주제를 철저히 리서치
context: fork
agent: Explore
---

$ARGUMENTS 를 철저히 리서치하라:
1. Glob·Grep으로 관련 파일 찾기
2. 코드 읽고 분석
3. 구체적 파일 참조와 함께 결과 요약
```

이는 [서브에이전트의 `skills` 프리로드](#ch7)와 **역방향** 관계입니다.

| 방식 | 시스템 프롬프트 | 작업 |
| --- | --- | --- |
| 스킬 `context: fork` | 에이전트 타입에서 | SKILL.md 내용 |
| 서브에이전트 `skills` 필드 | 서브에이전트 본문 | Claude의 위임 메시지 |

---

## 인자와 동적 컨텍스트

- **인자**: `$ARGUMENTS`(전체), `$0`·`$1`(위치별). `/fix-issue 123` → `$ARGUMENTS`가 `123`.
- **동적 주입**: `` !`명령` ``는 Claude가 보기 전에 실행되어 출력으로 치환. 여러 줄은 ` ```! ` 펜스.
- **스택**: 한 메시지에 여러 스킬을 앞에 쌓을 수 있음(최대 6개) — `/write-tests /fix-issue 123`.

---

## 스킬 vs CLAUDE.md vs 서브에이전트

| | 언제 로드 | 쓰임새 |
| --- | --- | --- |
| **CLAUDE.md** | 매 세션 전체 | 항상 필요한 사실·규칙 |
| **스킬** | 호출 시에만 | 가끔 필요한 절차·도메인 지식 |
| **서브에이전트** | 위임 시 격리 컨텍스트 | 고출력·전문 작업의 격리 |

---

## 문제 해결

- **트리거가 안 됨**: `description`에 사용자가 실제로 쓸 키워드를 넣기 → "무슨 스킬 있어?"로 목록 확인 → 직접 `/name` 호출.
- **너무 자주 트리거**: `description`을 더 구체적으로, 또는 `disable-model-invocation: true`.
- **설명이 잘림**: 스킬이 많으면 목록 예산에 맞춰 설명이 잘림. 핵심 용례를 앞에 두고, `skillListingBudgetFraction` 상향 또는 저우선 스킬을 `"name-only"`로.

---

## 핵심 요약

- 스킬 = `SKILL.md` 기반의 **온디맨드** 지식·절차. 컨텍스트를 아끼면서 능력을 확장한다.
- 디렉터리명이 명령어가 되고, `description`이 자동 호출을 좌우한다.
- `disable-model-invocation`·`allowed-tools`·`context: fork`로 호출 주체·권한·실행 위치를 통제한다.
- 커스텀 명령어는 이제 스킬로 통합됐다 — [명령어 챕터](#ch4)의 문법이 그대로 적용된다.
