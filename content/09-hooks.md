훅(Hook)은 Claude Code 생명주기의 특정 시점에 **자동으로 실행되는 셸 명령**입니다. 핵심은 **결정론(determinism)** 입니다. [CLAUDE.md](#ch5)의 지침은 "따라 주길 바라는" 조언이지만, 훅은 **Claude의 판단과 무관하게 반드시 실행**됩니다.

> "특정 시점에 예외 없이 매번 일어나야 하는 일"에는 훅을 쓰세요. 파일 편집 후 포맷팅, 위험한 명령 차단, 입력 대기 알림, 세션 시작 시 컨텍스트 주입 — 모두 훅의 영역입니다.

판단이 필요한 결정에는 셸 대신 모델을 쓰는 [프롬프트 훅·에이전트 훅](#prompt-based-hooks)도 있습니다.

---

## 첫 훅 — 입력 대기 알림

설정 파일에 `hooks` 블록을 추가합니다. 아래는 Claude가 입력을 기다릴 때 데스크톱 알림을 띄우는 예입니다(Linux).

```json
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "notify-send 'Claude Code' 'Claude Code needs your attention'"
          }
        ]
      }
    ]
  }
}
```

`/hooks`로 등록 여부를 확인합니다(이 메뉴는 **읽기 전용** — 추가·수정은 설정 JSON을 직접 편집하거나 Claude에게 부탁). Claude에게 "파일 편집마다 eslint를 돌리는 훅을 써줘"처럼 부탁하면 훅을 작성해 줍니다.

---

## 어디에 두는가

| 위치 | 스코프 | 공유 |
| --- | --- | --- |
| `~/.claude/settings.json` | 모든 프로젝트 | 아니오(머신 로컬) |
| `.claude/settings.json` | 단일 프로젝트 | 예(커밋 가능) |
| `.claude/settings.local.json` | 단일 프로젝트 | 아니오(gitignore) |
| 관리 정책 설정 | 조직 전체 | 예(관리자) |
| 플러그인 `hooks/hooks.json` | 플러그인 활성 시 | 예 |
| 스킬·에이전트 프론트매터 | 그 컴포넌트 활성 중 | 예 |

모든 훅을 끄려면 `"disableAllHooks": true`.

---

## 주요 훅 이벤트

이벤트가 발생하면 **매칭되는 훅이 병렬 실행**되고, 동일 명령은 자동 중복 제거됩니다.

| 이벤트 | 발생 시점 |
| --- | --- |
| `SessionStart` | 세션 시작·재개 |
| `UserPromptSubmit` | 프롬프트 제출 직후, Claude 처리 전 |
| `PreToolUse` | 도구 실행 **전**. 차단 가능 |
| `PermissionRequest` | 권한 대화가 뜰 때 |
| `PostToolUse` | 도구 실행 성공 후 |
| `PostToolUseFailure` | 도구 실행 실패 후 |
| `Notification` | 알림 전송 시 |
| `SubagentStart` / `SubagentStop` | 서브에이전트 시작·종료 |
| `Stop` | Claude가 응답을 마칠 때 |
| `PreCompact` / `PostCompact` | 컨텍스트 압축 전·후 |
| `InstructionsLoaded` | CLAUDE.md·규칙 로드 시 |
| `SessionEnd` | 세션 종료 |

`type`은 대부분 `"command"`(셸)이며, 이 외에 `"http"`(URL POST), `"mcp_tool"`(MCP 도구 호출), `"prompt"`(단일턴 LLM 판단), `"agent"`(도구를 쓰는 다중턴 검증, 실험적)가 있습니다.

---

## 매처(matcher)로 필터링

매처가 없으면 이벤트마다 무조건 실행됩니다. 도구 이벤트는 **도구 이름**으로 필터합니다.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "jq -r '.tool_input.file_path' | xargs npx prettier --write" }
        ]
      }
    ]
  }
}
```

`"Edit|Write"`는 파일 편집 도구에서만 발동(`,`도 동일 구분자). MCP 도구는 `mcp__<server>__<tool>` 형식이라 `mcp__github__.*` 같은 정규식으로 매칭합니다. 이벤트별 매처 대상:

| 이벤트 | 매처가 거르는 것 | 예 |
| --- | --- | --- |
| `PreToolUse`·`PostToolUse` | 도구 이름 | `Bash`, `Edit\|Write`, `mcp__.*` |
| `SessionStart` | 세션 시작 방식 | `startup`, `resume`, `clear`, `compact` |
| `Notification` | 알림 종류 | `permission_prompt`, `idle_prompt` |
| `SubagentStart`/`Stop` | 에이전트 타입 | `Explore`, 커스텀 이름 |

---

## 입력과 출력 — 훅이 Claude를 통제하는 법

훅은 **stdin(JSON 입력) · stdout/stderr · 종료 코드**로 소통합니다. 이벤트가 발생하면 이벤트별 데이터가 JSON으로 stdin에 전달됩니다.

```json
{
  "session_id": "abc123",
  "cwd": "/Users/sarah/myproject",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": { "command": "npm test" }
}
```

### 종료 코드

| 코드 | 의미 |
| --- | --- |
| **0** | 이의 없음. 정상 진행. `UserPromptSubmit`·`SessionStart`는 **stdout이 컨텍스트에 추가**됨 |
| **2** | 동작 **차단**. stderr가 Claude에게 피드백으로 전달되어 조정하게 함 |
| 그 외 | 진행하되 경고 표시 |

> PreToolUse에서 exit 0은 도구를 **승인하는 게 아닙니다** — 정상 권한 흐름이 그대로 적용됩니다. 차단하려면 exit 2 또는 아래의 구조화 JSON을 쓰세요.

### 구조화 JSON 출력

exit 0으로 하되 stdout에 JSON을 출력하면 더 정밀하게 통제합니다. PreToolUse의 권한 결정:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "grep 대신 rg를 쓰세요(성능)"
  }
}
```

`permissionDecision`은 `allow`(프롬프트 건너뜀)·`deny`(취소+사유 전달)·`ask`(정상 프롬프트). `UserPromptSubmit`은 `additionalContext`로 매 프롬프트에 컨텍스트를 주입합니다.

---

## 실전 예제

### 보호 파일 편집 차단 (PreToolUse)

`.claude/hooks/protect-files.sh`:

```bash
#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
PROTECTED_PATTERNS=(".env" "package-lock.json" ".git/")

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "차단: $FILE_PATH 는 보호 패턴 '$pattern' 에 해당" >&2
    exit 2
  fi
done
exit 0
```

`chmod +x`로 실행 권한을 주고, `PreToolUse`/`Edit|Write`로 등록합니다.

### 압축 후 컨텍스트 재주입 (SessionStart)

압축은 대화를 요약하며 중요 세부를 잃을 수 있습니다. `SessionStart`/`compact` 매처로 핵심을 다시 주입하세요(stdout이 컨텍스트에 추가됨).

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          { "type": "command", "command": "echo '알림: npm 아닌 Bun 사용. 커밋 전 bun test. 현재 스프린트: auth 리팩터.'" }
        ]
      }
    ]
  }
}
```

### 완료 전 테스트 검증 (프롬프트/에이전트 훅)

판단이 필요하면 `Stop` 훅에 모델을 씁니다. 모델은 yes/no만 반환하고, `"ok": false`면 사유를 Claude에게 돌려 계속 일하게 합니다.

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "prompt", "prompt": "모든 작업이 끝났는지 확인. 아니면 {\"ok\": false, \"reason\": \"남은 일\"} 로 응답." } ] }
    ]
  }
}
```

코드베이스 상태를 실제로 검증해야 하면 도구를 쓰는 `"type": "agent"` 훅(예: "테스트 스위트를 실행해 통과 확인")을 씁니다.

---

## 훅과 권한 모드

`PreToolUse` 훅은 **모든 권한 모드보다 먼저** 발동합니다 — `bypassPermissions`나 `--dangerously-skip-permissions`에서도 `deny`가 도구를 막습니다. 즉 **사용자가 권한 모드를 바꿔도 우회할 수 없는 정책**을 강제할 수 있습니다.

역은 성립하지 않습니다 — 훅의 `allow`는 설정의 deny 규칙을 뚫지 못합니다. **훅은 제약을 조일 수는 있어도 느슨하게 풀 수는 없습니다.**

---

## 문제 해결

| 증상 | 확인 |
| --- | --- |
| 훅이 안 뜸 | `/hooks`로 등록 확인, 매처는 **대소문자 구분**, 이벤트 타입 확인 |
| "hook error" | 샘플 JSON을 파이프해 수동 테스트, 절대경로/`${CLAUDE_PROJECT_DIR}` 사용, `chmod +x` |
| Stop 훅 무한 반복 | 8회 연속 차단 시 오버라이드됨. `stop_hook_active`를 파싱해 조기 종료 |
| JSON 검증 실패 | 셸 프로필의 `echo`가 stdout을 오염 — 대화형 셸에서만 실행되게 감싸기 |

> **보안 주의**: 훅은 당신 권한으로 임의 셸 명령을 실행합니다. 공유·프로덕션 환경에 배포하기 전 반드시 검토하세요.

---

## 핵심 요약

- 훅 = 생명주기 시점에 **결정론적으로** 실행되는 자동화. CLAUDE.md가 조언이라면 훅은 강제.
- 설정 파일의 `hooks` 블록에 이벤트·매처·명령으로 정의한다.
- stdin(JSON)·종료코드(0/2)·구조화 JSON으로 Claude의 동작을 차단·허용·컨텍스트 주입한다.
- 포맷팅·보호 파일 차단·압축 후 재주입·완료 전 검증이 대표 용례. **정책 강제는 훅으로, 조언은 [CLAUDE.md](#ch5)로.**
