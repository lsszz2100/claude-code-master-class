[3장](#ch3)에서 본 최신 모델 — **Opus 5·Fable 5·Sonnet 5** — 은 이전 세대보다 훨씬 똑똑하고 자율적입니다. 기존 Opus 4.8 프롬프트로도 잘 동작하지만, **더 자율적으로 행동하기 때문에** 몇몇 습관은 반대로 튜닝해야 합니다. 이 챕터는 Anthropic의 Opus 5 프롬프트 가이드를 바탕으로, 실무에서 가장 자주 조정하는 패턴을 모았습니다.

> **큰 원칙:** 모델이 좋아질수록 **덜 지시**해야 합니다. 예전 모델을 밀어붙이려고 넣었던 스캐폴딩(검증 강제·재확인 지시 등)이 최신 모델에선 **과잉 행동을 유발**해 토큰만 낭비합니다. 이런 지시는 **빼는 것**이 개선입니다.

---

## 1) 응답이 길어졌다 → 간결하게 지시

Opus 5의 기본 사용자 응답은 이전 Opus보다 **깁니다**. **effort는 "얼마나 생각하는지"를 조절할 뿐, "얼마나 말하는지"는 아닙니다** — effort를 낮춰도 보이는 응답이 확실히 짧아지지 않습니다. 길이는 **명시적으로 프롬프트**하세요.

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

## 2) 진행 상황을 많이 내레이션한다 → 케이던스 지정

에이전틱 작업 중 Opus 5는 "이제 무엇을 할지"를 자주 예고하고, 턴당 출력이 이전보다 깁니다. **소통 방식을 명시**하면 조절됩니다.

```text
Before your first tool call, say in one sentence what you're about to do.
While working, give a brief update only when you find something important or
change direction. When you finish, lead with the outcome: your first sentence
should answer "what happened" or "what did you find," with supporting detail after.
```

> 내레이션을 **늘리거나** 스타일을 바꾸고 싶을 때도 같은 레버 — 원하는 형태를 예시로 보여 주세요. "**하지 말라**"는 부정 지시보다 "**이렇게 하라**"는 긍정 예시가 더 잘 먹힙니다.

---

## 3) 파일 산출물도 길어졌다 → 길이 보정

대화 장황함과 별개로, Opus 5가 **디스크에 쓰는 파일**(리포트·마크다운·요약)도 이전보다 깁니다. Claude가 문서를 작성하는 제품이라면 길이 기준을 명시하세요.

```text
Match the length of written documents to what the task needs: cover the substance,
but do not pad with filler sections, redundant summaries, or boilerplate.
```

---

## 4) 스스로 검증한다 → 검증 지시를 빼라 + 범위 제약

Opus 5는 **시키지 않아도 자기 작업을 검증**합니다. 프롬프트에 "비자명한 작업엔 최종 검증 단계를 넣어라", "서브에이전트로 검증해라" 같은 지시가 있으면 **제거**하세요 — 최신 모델에선 **과잉 검증**을 유발해 토큰만 낭비합니다([하네스의 레거시 스캐폴딩](#ch13)도 마찬가지).

또한 Opus 5는 **요청하지 않은 단계를 더하거나 범위를 넓히는** 경향이 있습니다. 좁은 작업은 범위를 명시적으로 제약하세요.

```text
Deliver what was asked, at the scope intended. Make routine judgment calls yourself,
and check in only when different readings of the request would lead to materially
different work. If the request seems mistaken or a better approach exists, say so in
a sentence and continue with the task as asked rather than quietly narrowing,
widening, or transforming it. Finish the whole task, and stop short of actions that
are clearly beyond what was asked.
```

---

## 5) 서브에이전트를 더 적극 위임한다 → 캡을 걸어라

Opus 5는 이전보다 [서브에이전트](#ch7)에 **더 잘 위임**합니다. 위임은 **진짜 독립적이고 큰** 작업에선 이득이지만, 작은 작업에 적용하면 비용·시간이 배가됩니다. 어떤 경우에 위임할지 명시하거나 결정론적 상한을 두세요.

```text
Delegate to a subagent only for large tasks that are genuinely independent and
parallelizable, such as a wide multi-file investigation. Do not delegate work you can
finish yourself in a handful of tool calls, and do not use subagents to verify or
double-check your own work. If one subagent can complete the task, use one rather
than several, and keep spawn counts low.
```

---

## 6) 스스로 고친다 → 재확인 지시를 빼라

Opus 5는 자기 실수를 **알아서 잡아 고칩니다**. "답을 다시 확인해라", "응답 전 재검증해라" 같은 지시는 모델의 기존 행동과 **겹쳐** 비용만 늘립니다 — 넣지 마세요.

다만 이전 발언을 **정정하는 내레이션**이 늘어, 사용자 대면 제품에선 거슬릴 수 있습니다. 의미 있는 정정만 남기려면:

```text
Only correct an earlier statement when the error would change the user's code,
conclusions, or decisions. State corrections plainly and briefly, then continue.
For slips that change nothing for the user, make the fix and move on without noting it.
```

---

## 7) thinking을 끄면 생기는 아티팩트

Opus 5는 **사고(thinking)가 기본 켜짐**이고, 끄는 것은 **effort `high` 이하에서만** 가능합니다. 사고를 끄면 두 가지 아티팩트가 가끔 나타납니다.

- **도구 호출이 텍스트로 샘**: 구조화된 `tool_use` 블록 대신 도구 호출을 **사용자 텍스트에 써 버려** 실제 실행되지 않음(검색 등 도구 위주 작업에서 흔함).
- **내부 XML 태그 누수**: `<thinking>` 같은 내부 태그가 응답에 노출.

> **최선의 완화책은 사고를 끄지 말고, 대신 effort를 낮춰 비용을 통제하는 것**입니다 — 대부분의 작업에서 "**사고 켜짐 + `low` effort**"가 "사고 꺼짐"보다 낫습니다. 꼭 꺼야 한다면 단일 지시로 두 아티팩트를 함께 완화하세요(태그를 **이름으로 지목하지 마세요** — 오히려 누수가 늘어납니다).

```text
When you use a tool, you may say a brief sentence first. If no tool can express what
the user asked for, say so instead of guessing. Do not include internal or system
XML tags in your response.
```

---

## 마이그레이션 노트 (Opus 4.8 → Opus 5)

- Opus 5는 기존 4.8 프롬프트로도 **바로 잘 동작**합니다 — 위 패턴은 "튜닝이 필요할 때"의 조정입니다.
- **사고가 기본 켜짐**으로 바뀌었고, 비활성화는 **effort `high` 이하에서만** 됩니다.
- **완전한 작업 명세를 처음에 한 번에** 주고 자율 실행에 맡길 때 가장 강합니다([오케스트레이션](#ch11)의 "구체적으로 지시하라"와 동일).
- effort 기본값을 이전 모델에서 가져왔다면 **자신의 평가셋으로 재스윕**하세요.

---

## 핵심 요약

- 최신 모델은 **더 자율적** — 예전의 "밀어붙이는" 지시(검증 강제·재확인)는 **빼는 것**이 개선이다.
- **길이·내레이션·문서 길이**는 effort가 아니라 **명시적 프롬프트**로 조절한다(긍정 예시가 효과적).
- **범위를 좁히고, 서브에이전트 위임에 캡**을 걸어 과잉 행동·비용을 막는다.
- **사고는 끄지 말고 `low` effort로** 비용을 통제한다 — 끄면 도구호출 누수·XML 태그 누수가 생긴다.
