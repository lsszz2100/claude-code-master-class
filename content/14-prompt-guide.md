[3장](#ch3)에서 본 최신 모델 — **Fable 5.1·Opus 5·Sonnet 5** — 은 이전 세대보다 훨씬 똑똑하고 자율적입니다. 기존 프롬프트로도 기본 동작하지만, **더 자율적으로 행동하기 때문에** 몇몇 습관은 반대로 튜닝해야 합니다. 이 챕터는 Anthropic 공식 **Opus 5 프롬프트 가이드**와 최신 **Fable 5.1 프롬프트 가이드("Prompting Claude Fable 5.1")**를 바탕으로, 실무 에이전틱 워크플로에서 필수적인 패턴을 모았습니다.

> **큰 원칙:** 모델이 좋아질수록 **덜 지시**해야 합니다. 예전 모델을 밀어붙이려고 넣었던 스캐폴딩(검증 강제·재확인 지시·단계별 번호 강요 등)이 최신 모델에선 **과잉 행동을 유발**해 토큰만 낭비합니다. 이런 지시는 **빼는 것**이 개선입니다.

---

## 1부: 최신 모델 공통 튜닝 패턴 (Opus 5 & Fable)

### 1) 응답이 길어졌다 → 간결하게 지시

최신 세대의 기본 사용자 응답은 이전 세대보다 **깁니다**. **effort는 "얼마나 생각하는지"를 조절할 뿐, "얼마나 말하는지"는 아닙니다** — effort를 낮춰도 보이는 응답이 확실히 짧아지지 않습니다. 길이는 **명시적으로 프롬프트**하세요.

```text
Keep responses focused, brief, and concise. Keep disclaimers and caveats short,
and spend most of the response on the main answer. When asked to explain something,
give a high-level summary unless an in-depth explanation is specifically requested.
```

긴 시스템 프롬프트에서는 끝부분에 짧은 리마인더를 함께 두면 효과적입니다.

```text
<tone_preference>
Keep outputs reasonably concise.
</tone_preference>
```

---

### 2) 진행 상황을 많이 내레이션한다 → 케이던스 지정

에이전틱 작업 중 최신 모델은 "이제 무엇을 할지"를 자주 예고하고, 턴당 출력이 이전보다 깁니다. **소통 방식을 명시**하면 조절됩니다.

```text
Before your first tool call, say in one sentence what you're about to do.
While working, give a brief update only when you find something important or
change direction. When you finish, lead with the outcome: your first sentence
should answer "what happened" or "what did you find," with supporting detail after.
```

> 내레이션을 **늘리거나** 스타일을 바꾸고 싶을 때도 같은 레버 — 원하는 형태를 예시로 보여 주세요. "**하지 말라**"는 부정 지시보다 "**이렇게 하라**"는 긍정 예시가 더 잘 먹힙니다.

---

### 3) 파일 산출물도 길어졌다 → 길이 보정

대화 장황함과 별개로, 최신 모델이 **디스크에 쓰는 파일**(리포트·마크다운·요약)도 이전보다 깁니다. Claude가 문서를 작성하는 제품이라면 길이 기준을 명시하세요.

```text
Match the length of written documents to what the task needs: cover the substance,
but do not pad with filler sections, redundant summaries, or boilerplate.
```

---

### 4) 스스로 검증한다 → 검증 지시를 빼라 + 범위 제약

최신 모델은 **시키지 않아도 자기 작업을 검증**합니다. 프롬프트에 "비자명한 작업엔 최종 검증 단계를 넣어라", "서브에이전트로 검증해라" 같은 지시가 있으면 **제거**하세요 — 최신 모델에선 **과잉 검증**을 유발해 토큰만 낭비합니다([하네스의 레거시 스캐폴딩](#ch13)도 마찬가지).

또한 요청하지 않은 단계를 더하거나 범위를 넓히는 경향이 있습니다. 좁은 작업은 범위를 명시적으로 제약하세요.

```text
Deliver what was asked, at the scope intended. Make routine judgment calls yourself,
and check in only when different readings of the request would lead to materially
different work. If the request seems mistaken or a better approach exists, say so in
a sentence and continue with the task as asked rather than quietly narrowing,
widening, or transforming it. Finish the whole task, and stop short of actions that
are clearly beyond what was asked.
```

---

### 5) 서브에이전트를 더 적극 위임한다 → 캡을 걸어라

이전보다 [서브에이전트](#ch7)에 **더 잘 위임**합니다. 위임은 **진짜 독립적이고 큰** 작업에선 이득이지만, 작은 작업에 적용하면 비용·시간이 배가됩니다. 어떤 경우에 위임할지 명시하거나 결정론적 상한을 두세요.

```text
Delegate to a subagent only for large tasks that are genuinely independent and
parallelizable, such as a wide multi-file investigation. Do not delegate work you can
finish yourself in a handful of tool calls, and do not use subagents to verify or
double-check your own work. If one subagent can complete the task, use one rather
than several, and keep spawn counts low.
```

---

### 6) 스스로 고친다 → 재확인 지시를 빼라

자기 실수를 **알아서 잡아 고칩니다**. "답을 다시 확인해라", "응답 전 재검증해라" 같은 지시는 모델의 기존 행동과 **겹쳐** 비용만 늘립니다 — 넣지 마세요.

다만 이전 발언을 **정정하는 내레이션**이 늘어, 사용자 대면 제품에선 거슬릴 수 있습니다. 의미 있는 정정만 남기려면:

```text
Only correct an earlier statement when the error would change the user's code,
conclusions, or decisions. State corrections plainly and briefly, then continue.
For slips that change nothing for the user, make the fix and move on without noting it.
```

---

### 7) thinking을 끄면 생기는 아티팩트

Opus 5는 **사고(thinking)가 기본 켜짐**(Fable 5.1/5는 상시 켜짐)이고, 끄는 것은 **effort `high` 이하에서만** 가능합니다. 사고를 끄면 두 가지 아티팩트가 가끔 나타납니다.

- **도구 호출이 텍스트로 샘**: 구조화된 `tool_use` 블록 대신 도구 호출을 **사용자 텍스트에 써 버려** 실제 실행되지 않음(검색 등 도구 위주 작업에서 흔함).
- **내부 XML 태그 누수**: `<thinking>` 같은 내부 태그가 응답에 노출.

> **최선의 완화책은 사고를 끄지 말고, 대신 effort를 낮춰 비용을 통제하는 것**입니다 — 대부분의 작업에서 "**사고 켜짐 + `low` effort**"가 "사고 꺼짐"보다 낫습니다. 꼭 꺼야 한다면 단일 지시로 두 아티팩트를 함께 완화하세요(태그를 **이름으로 지목하지 마세요** — 오히려 누수가 늘어납니다).

```text
When you use a tool, you may say a brief sentence first. If no tool can express what
the user asked for, say so instead of guessing. Do not include internal or system
XML tags in your response.
```

---

---

## 2부: Claude Fable 5.1 공식 실전 가이드

2026년 9월 출시된 **Claude Fable 5.1**(`claude-fable-5-1`)은 최상위 지능과 복잡한 장기 에이전트 자율 작업에 특화된 모델입니다. Anthropic 공식 가이드(*Prompting Claude Fable 5.1*)가 권고하는 핵심 패턴입니다.

### 1) 모든 effort 레벨을 시험하라 (Consider all effort levels)

Fable 5.1의 기본 effort는 **`high`**입니다. 하지만 이전 세대와 이름이 같다고 사고량이 같지 않습니다.
- **`medium`**: Fable 5 수준의 높은 품질을 유지하면서 **비용과 지연 시간을 크게 절감**합니다.
- **`low`**: Opus 5나 Sonnet 5 수준의 비용으로 동작하면서도 더 뛰어난 벤치마크 점수를 냅니다.
- **`xhigh` / `max`**: 고난도 추론 및 방대한 분석 작업 전용입니다.

> **권고:** 무조건 `high`에 고정하지 말고, 루틴한 작업에는 `medium`이나 `low`로 내려 비용을 최적화하세요.

---

### 2) 사용자 대면 진행 상황 업데이트 유도 (Ask for progress updates)

Fable 5.1은 긴 도구 호출 체인에서 **중간 사용자 안내를 생략하고 침묵**하는 경향이 이전보다 큽니다.
1. **클라이언트 수신 설정:** 모델의 중간 노트는 `progress-update` 형태의 thinking 블록으로 옵니다. 기본값 `omitted` 대신 API 헤더 `display: "updates"` 또는 `"summarized"`를 사용하세요.
2. **레거시 억제 지침 제거:** 프롬프트에 "최종 응답 전까지 중간 발견을 말하지 말라" 같은 레거시 문구가 있다면 제거하세요.
3. **진행 업데이트 지침 주입:**

```text
Before you start, say in a line what you're about to do; brief updates while you work
help the user follow along. Close with a short recap that stands on its own — what you
found, what you did, and what's next — so a reader who only sees the last message has
the full picture.
```

---

### 3) 에이전트 루프에서 독립 도구 호출 배치 병렬화 (Batch independent tool calls)

코딩 및 에디터 환경에서 Fable 5.1은 독립적인 파일 읽기/조회 도구를 **한 턴에 하나씩 순차 호출**하는 경향이 있습니다. 이는 품질엔 영향이 없지만 라운드트립 시간과 토큰을 낭비합니다. 아래 한 줄 넛지로 **단일 턴 병렬 호출**을 유도하세요:

```text
First privately list what you need next; then request every item that doesn't depend
on another's result in this one response.
```

> **API 팁:** 매 턴 도구 결과 뒤에 턴 스코프 시스템 메시지(`clear_at: "next_user_message"`, beta)로 이 넛지를 주입하면 가장 깔끔합니다.

---

### 4) 대화 기록은 반드시 추가 전용(Append-only) 유지

Fable 5.1의 thinking 블록은 **그 블록을 생성한 정확한 대화 컨텍스트에서만 유효**합니다(2026년 8월 31일 이후 계정).
- 이전 턴의 텍스트나 도구 결과를 수정·삭제하면 **프롬프트 캐시가 깨질 뿐만 아니라, 그 뒤에 오는 모든 thinking 블록이 무효화**됩니다.
- 도구 넛지나 메시지는 과거 턴을 고치지 말고 반드시 **배열 끝에 추가(Append)**하세요.

---

### 5) 글쓰기 밀도 & 채팅 포맷팅 (Writing density & formatting)

- **밀도 조절:** Fable 5.1은 불필요한 상투어를 쓰지 않지만, 문장이 길어지고 단락 구분이 적어 텍스트가 빽빽해질 수 있습니다. "3~4문장마다 단락을 나누고 핵심은 앞에 두라"는 지침이 유용합니다.
- **자연스러운 산문 선호:** Fable 5.1은 기본적으로 불릿 기호나 볼드 강조를 덜 씁니다. 과거 모델의 과도한 불릿을 막으려고 넣었던 **"불릿/볼드를 쓰지 말라"는 레거시 억제 지침은 제거**하세요 — 오히려 가독성을 해칩니다.

---

### 6) 전체 파일 재작성 대신 타겟 편집 선호 (Prefer targeted edits)

작은 코드를 고칠 때도 파일 전체를 다시 쓰는 경향이 있습니다. 토큰 낭비와 충돌을 방지하려면 타겟 편집을 명시하세요:

```text
Make targeted edits to existing files rather than rewriting the entire file.
Keep unchanged code and comments intact.
```

---

### 7) 끝까지 작업을 완수하라 (Finish the whole task)

비동기 에이전트 루프에서 Fable 5.1은 실제로 도구를 실행하는 대신 "다음에 무엇을 할지" 설명만 하고 턴을 마치는 경우가 있습니다. 명확한 완수 넛지를 제공하세요:

```text
Do not stop after planning or describing next steps. Execute all necessary tool calls
and complete the implementation until the goal is fully achieved.
```

---

### 8) 컨텍스트 압축 요약 시 보존 항목 명시 (Compaction summaries)

대화가 길어져 [컨텍스트 압축](#ch12)을 진행할 때, Fable 5.1에게 무엇을 반드시 남겨야 하는지 명시하세요:

```text
Summarize the transcript inside <summary></summary> tags.
Retain all architectural decisions made, paths of modified or created files,
active constraints, and unresolved issues. Do not retain full code diffs or
intermediate research tool outputs.
```

---

### 9) 작업 범위와 테스트 파일 한정 (Keep changes and tests in scope)

Fable 5.1은 자율성이 뛰어나 요청하지 않은 주변 코드까지 손대거나, 사소한 변경에도 테스트 파일을 과도하게 생성할 수 있습니다. 

```text
Keep code changes strictly scoped to the requested task. Do not refactor unrelated code,
modify files outside the feature scope, or commit extraneous test files beyond what is
needed to verify the change.
```

---

### 10) xhigh/max effort 긴 출력 시 토큰 여유 확보 & 서브에이전트 병렬화

- **출력 토큰 예산:** `xhigh`나 `max` effort에서는 모델이 사고(thinking) 단계에서 전체 초안을 길게 작성한 뒤 본문으로 출력하므로, `max_tokens`를 최소 16,000 이상으로 넉넉히 잡아야 토큰 잘림을 방지할 수 있습니다.
- **서브에이전트 논블로킹:** 서브에이전트를 호출했을 때 리드 에이전트가 멈추고 기다리지 않게 하세요. 리드가 계속 독자적인 작업을 이어갈 때 전체 완료 시간이 단축됩니다.

---

## 마이그레이션 노트

### Fable 5 → Fable 5.1 마이그레이션
- **모델 ID 변경**: `claude-fable-5` → `claude-fable-5-1`.
- **캐시 읽기 비용 75% 절감**: $1.00/M → **$0.25/M** 토큰. 캐시를 적극 활용하는 긴 세션과 에이전틱 루프에서 비용 절감 효과가 극대화됩니다.
- **지식 컷오프**: 2026년 1월 → **2026년 6월**.
- **강제 도구 선택(forced tool_choice) 주의**: 엄격한 특정 도구 강제 모드가 제한되므로 API 옵션을 점검하세요.
- **이전 턴 수정 금지**: thinking 블록의 유효성을 위해 Append-only 대화 구조를 철저히 준수하세요.

### Opus 4.8 → Opus 5 마이그레이션
- 기존 프롬프트로도 기본 동작하지만, **사고가 기본 켜짐**으로 변경되었으며 끄기는 effort `high` 이하에서만 가능합니다.
- 예전의 장황한 검증 스캐폴딩을 제거하고, 작업 명세를 초반에 구체적으로 한 번에 전달하는 것이 유리합니다.

---

## 핵심 요약

- 최신 모델은 **더 자율적** — 예전의 "밀어붙이는" 지시(검증 강제·재확인·번호 스캐폴딩)는 **빼는 것**이 개선이다.
- **Fable 5.1**은 최고 지능 티어로, **캐시 읽기 단가가 75% 인하($0.25/M)**되어 에이전틱 작업에 최적화되었다.
- **Fable 5.1 튜닝 3대 핵심:**
  1. `medium`/`low` effort도 적극 검토(품질 대비 비용 최적화).
  2. 에이전트 루프에서 **독립 도구 호출 병렬 배치 넛지** 제공.
  3. **대화 기록은 반드시 Append-only**로 유지(이전 턴 수정 시 캐시 및 thinking 블록 무효화).
- **길이·내레이션·문서 길이**는 effort가 아니라 **명시적 프롬프트**로 조절한다.
- **사고는 끄지 말고 `low` effort로** 비용을 통제한다 — 끄면 도구호출 누수·XML 태그 누수가 생긴다.
