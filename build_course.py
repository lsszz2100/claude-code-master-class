# -*- coding: utf-8 -*-
"""
build_course.py
Claude Code 마스터 클래스 — 챕터 마크다운 → 단일 강의 사이트(index.html).
Claude Code 확장 기능 전반을 다루는 자체 집필 강의. 외부 저장소 참조 없음.
- 사이드바 TOC + scroll-spy, 라이트/다크 토글, mermaid(jsDelivr @11 ESM), highlight.js
- 챕터간 링크는 인페이지 앵커로 재작성
"""
import os
import re
import html
import json
import datetime
import markdown

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "content")
OUT = os.path.join(HERE, "index.html")

SITE_URL = "https://claude-code-tutorial-ko.vercel.app"
SITE_NAME = "Claude Code 마스터 클래스"
AUTHOR = "AI_Innovation_Studio"

# 챕터 순서: (파일명, 사이드바 제목)
CHAPTERS = [
    ("01-intro-install.md", "Claude Code란? · 설치"),
    ("02-basics-permissions.md", "첫 세션 · 권한 · 플랜 모드"),
    ("03-models.md", "모델과 성능"),
    ("04-commands.md", "명령어 · 슬래시 커맨드"),
    ("05-claude-md.md", "CLAUDE.md · 프로젝트 지침"),
    ("06-memory.md", "자동 기억 (Agent Memory)"),
    ("07-subagents.md", "서브에이전트"),
    ("08-skills.md", "스킬"),
    ("09-hooks.md", "훅 (Hooks)"),
    ("10-mcp-plugins.md", "MCP · 플러그인 · 확장"),
    ("11-orchestration.md", "오케스트레이션 & 실전 워크플로"),
    ("12-context-engineering.md", "컨텍스트 엔지니어링"),
    ("13-harness-loop.md", "하네스 & 루프 엔지니어링"),
    ("14-prompt-guide.md", "최신 모델 프롬프트 가이드"),
    ("15-playground.md", "플레이그라운드"),
    ("16-appendix.md", "부록 · 알면 좋은 것들"),
    ("17-references.md", "참고 자료 · GitHub 리소스"),
]

# 인페이지 앵커로 유지할 대상 (그 외 #앵커 링크는 굵은 텍스트로 치환)
ANCHOR_KEEP = {"top"} | {f"ch{i}" for i in range(1, len(CHAPTERS) + 1)}

# 챕터별 확인 퀴즈: 각 문항 (질문, [보기...], 정답 인덱스(0-based), 해설)
QUIZZES = {
    4: [
        ("커스텀 명령어(`.claude/commands/`)는 2026년 현재 무엇으로 통합되었나요?",
         ["훅(Hook)", "스킬(Skill)", "서브에이전트", "MCP 서버"], 1,
         "커스텀 명령어는 스킬로 통합됐습니다. 기존 `.claude/commands/` 파일도 계속 작동합니다."),
        ("스킬·명령에서 `` !`git diff` `` 문법은 무엇을 하나요?",
         ["Claude에게 명령을 설명만 함", "Claude가 보기 전에 셸에서 실행해 출력으로 치환", "커밋을 자동 실행", "파일을 삭제"], 1,
         "동적 컨텍스트 주입 — 명령이 먼저 실행되어 실제 출력이 프롬프트에 인라인됩니다."),
        ("무관한 작업으로 넘어갈 때 컨텍스트를 리셋하는 명령은?",
         ["/compact", "/context", "/clear", "/model"], 2,
         "`/clear`는 컨텍스트를 완전히 리셋합니다. 작업 전환 시 습관적으로 쓰세요."),
    ],
    5: [
        ("CLAUDE.md 파일의 권장 최대 길이는?",
         ["50줄", "200줄", "1000줄", "제한 없음"], 1,
         "200줄 이하가 목표입니다. 길수록 컨텍스트를 더 먹고 준수율이 떨어집니다."),
        ("팀과 버전 관리로 공유할 프로젝트 지침은 어디에 두나요?",
         ["~/.claude/CLAUDE.md", "./CLAUDE.md (또는 ./.claude/CLAUDE.md)", "./CLAUDE.local.md", "관리 정책 위치"], 1,
         "프로젝트 루트의 CLAUDE.md는 커밋되어 팀과 공유됩니다. local은 개인용, ~/.claude는 사용자 전역입니다."),
        ("반드시 특정 시점에 강제로 실행돼야 하는 규칙은 어디에 두는 게 맞나요?",
         ["CLAUDE.md에 IMPORTANT로 강조", "훅(Hook)", "자동 기억", "그냥 대화로 지시"], 1,
         "CLAUDE.md는 조언(컨텍스트)일 뿐입니다. 강제가 필요하면 결정론적인 훅을 쓰세요."),
    ],
    7: [
        ("서브에이전트를 쓰는 가장 핵심적인 이유는?",
         ["더 똑똑한 모델을 쓰려고", "독립 컨텍스트로 메인 대화의 컨텍스트를 보호하려고", "권한 프롬프트를 없애려고", "코드를 더 빨리 쓰려고"], 1,
         "장황한 출력은 서브에이전트 컨텍스트에만 남고 요약만 메인으로 돌아옵니다 — 컨텍스트 보호가 핵심입니다."),
        ("Claude가 어떤 서브에이전트에 자동 위임할지 결정하는 프론트매터 필드는?",
         ["name", "tools", "description", "model"], 2,
         "`description`이 자동 위임의 트리거입니다. \"use proactively\" 같은 표현으로 적극 위임을 유도할 수 있습니다."),
        ("내장 Explore·Plan 에이전트가 속도를 위해 로드하지 않는 것은?",
         ["작업 디렉터리 정보", "CLAUDE.md와 git 상태", "읽기 전용 도구", "시스템 프롬프트"], 1,
         "Explore·Plan은 CLAUDE.md와 git 상태를 건너뛰어 리서치를 가볍고 빠르게 유지합니다."),
    ],
    8: [
        ("스킬 본문(SKILL.md 내용)은 언제 컨텍스트에 로드되나요?",
         ["매 세션 항상", "스킬이 호출(사용)될 때만", "프로젝트를 열 때", "절대 로드 안 됨"], 1,
         "온디맨드 로딩이 스킬의 핵심 장점입니다. 긴 참조 자료도 쓰이기 전엔 컨텍스트 비용이 거의 0입니다."),
        ("Claude가 스킬을 자동으로 호출하지 못하게 하고 사용자만 `/name`으로 실행하게 하려면?",
         ["user-invocable: false", "disable-model-invocation: true", "allowed-tools 비우기", "context: fork"], 1,
         "`disable-model-invocation: true`는 부작용이 있는 워크플로(/deploy 등)에 적합합니다."),
        ("스킬을 격리된 서브에이전트 컨텍스트에서 실행하게 하는 프론트매터는?",
         ["context: fork", "memory: project", "paths", "model: haiku"], 0,
         "`context: fork`를 넣으면 스킬 본문이 서브에이전트의 프롬프트가 되어 격리 실행됩니다."),
    ],
    6: [
        ("자동 기억(Auto memory)에 노트를 쓰는 주체는?",
         ["사용자", "Claude", "팀 관리자", "빌드 시스템"], 1,
         "CLAUDE.md는 당신이 쓰지만, 자동 기억은 Claude가 스스로 유용하다고 판단한 것을 기록합니다."),
        ("매 세션 시작 시 로드되는 자동 기억의 색인 파일은?",
         ["CLAUDE.md", "MEMORY.md (앞 200줄/25KB)", "index.md", "notes.md"], 1,
         "`MEMORY.md`가 색인 역할을 하며 앞 200줄 또는 25KB만 로드됩니다. 주제 파일은 필요 시 읽습니다."),
        ("서브에이전트 기억의 권장 기본 스코프는? (버전 관리로 공유 가능)",
         ["user", "project", "local", "global"], 1,
         "`project` 스코프는 `.claude/agent-memory/`에 저장되어 버전 관리로 팀과 공유됩니다."),
    ],
    11: [
        ("Claude Code의 거의 모든 모범 사례가 수렴하는 단 하나의 제약은?",
         ["API 비용", "컨텍스트 창 관리(찰수록 성능 저하)", "모델 속도", "네트워크 지연"], 1,
         "컨텍스트 창은 가장 중요한 자원입니다. 찰수록 성능이 떨어지므로 /clear·서브에이전트로 관리합니다."),
        ("접근법이 불확실하거나 여러 파일을 건드릴 때 권장되는 워크플로 순서는?",
         ["구현→탐색→계획→커밋", "탐색→계획→구현→커밋", "계획→커밋→구현→탐색", "커밋→구현→계획→탐색"], 1,
         "탐색(플랜 모드)→계획→구현→커밋. 단, 한 문장으로 diff를 설명할 수 있으면 계획을 건너뛰세요."),
        ("같은 이슈로 두 번 넘게 교정했을 때 권장되는 행동은?",
         ["계속 교정한다", "`/clear` 후 배운 것을 반영한 더 나은 프롬프트로 시작", "모델을 바꾼다", "세션을 종료한다"], 1,
         "두 번 교정했다면 컨텍스트가 실패한 시도로 오염된 상태입니다. 깨끗한 세션이 거의 항상 낫습니다."),
    ],
    9: [
        ("훅(Hook)이 CLAUDE.md와 근본적으로 다른 점은?",
         ["더 짧게 쓸 수 있다", "Claude의 판단과 무관하게 결정론적으로 실행된다", "컨텍스트를 안 먹는다", "팀과 공유된다"], 1,
         "CLAUDE.md는 조언이지만 훅은 강제입니다 — 특정 시점에 예외 없이 실행됩니다."),
        ("PreToolUse 훅에서 도구 실행을 '차단'하려면 어떤 종료 코드를 쓰나요?",
         ["exit 0", "exit 1", "exit 2", "exit 127"], 2,
         "exit 2는 동작을 차단하고 stderr를 Claude에게 피드백으로 전달합니다. exit 0은 정상 진행입니다."),
        ("파일 편집 직후 자동으로 포맷터(prettier)를 돌리려면 어느 이벤트를 쓰나요?",
         ["PreToolUse", "PostToolUse (matcher: Edit|Write)", "SessionStart", "Stop"], 1,
         "PostToolUse는 도구 실행 성공 후 발동합니다. Edit|Write 매처로 파일 편집 시에만 실행합니다."),
    ],
    1: [
        ("Claude Code를 사용하려면 어떤 계정이 필요한가요?",
         ["무료 Claude.ai 요금제면 충분", "Pro/Max/Team/Enterprise/Console 중 하나", "GitHub 계정만 있으면 됨", "계정 불필요"], 1,
         "무료 Claude.ai로는 사용할 수 없습니다. Pro/Max/Team/Enterprise/Console 또는 제3자 API 제공자가 필요합니다."),
        ("자동 업데이트를 지원하는 권장 설치 방법은?",
         ["npm install -g", "네이티브 설치 (curl … | bash / irm … | iex)", "소스 빌드", "Homebrew"], 1,
         "네이티브 설치가 가장 간단하고 백그라운드 자동 업데이트됩니다. brew·winget·npm은 수동 업데이트가 필요합니다."),
        ("새 코드베이스에 온보딩하는 가장 효과적인 방법은?",
         ["전체 파일을 한 번에 읽게 시킨다", "시니어 엔지니어에게 하듯 질문을 던진다", "CLAUDE.md부터 작성한다", "테스트부터 돌린다"], 1,
         "\"로깅은 어떻게 동작해?\" 같은 질문을 직접 던지는 것이 가장 효과적인 온보딩입니다."),
    ],
    2: [
        ("권한 모드를 순환 전환하는 단축키는?",
         ["Ctrl+C", "Shift+Tab", "Tab", "Ctrl+R"], 1,
         "Shift+Tab으로 default→acceptEdits→plan→auto→bypassPermissions를 순환합니다."),
        ("변경 없이 코드베이스를 이해하고 계획만 세우는 모드는?",
         ["acceptEdits", "plan", "auto", "bypassPermissions"], 1,
         "plan 모드는 읽기 전용 탐색으로, 엉뚱한 문제를 푸는 것을 막아 줍니다."),
        ("실행 중인 Claude를 멈추되 컨텍스트를 보존해 방향을 바꾸는 키는?",
         ["Esc", "Ctrl+D", "q", "Ctrl+Z"], 0,
         "Esc로 중단하면 컨텍스트가 보존되어 바로 방향을 재지정할 수 있습니다. Esc 두 번은 되감기 메뉴."),
    ],
    3: [
        ("복잡한 에이전틱 코딩에 Anthropic이 권장하는 기본 모델은?(2026)",
         ["Fable 5", "Opus 5", "Sonnet 5", "Haiku 4.5"], 1,
         "복잡한 에이전틱 코딩·엔터프라이즈엔 Opus 5, 최고 능력엔 Fable 5를 권합니다. Opus 4.8 등은 레거시입니다."),
        ("Claude 5 세대(Opus 5·Sonnet 5)의 기본 effort 레벨은?",
         ["low", "medium", "high", "xhigh"], 2,
         "기본은 high입니다(Claude API·Claude Code). 어려운 코딩·에이전틱엔 xhigh로 올리고, 비용·속도엔 low/medium을 적극 씁니다."),
        ("가장 강력한(최고 지능) 널리 출시된 모델은?",
         ["Opus 5", "Fable 5", "Sonnet 5", "Haiku 4.5"], 1,
         "최고 지능 티어는 Fable 5입니다. 복잡 코딩·에이전틱의 권장 기본은 Opus 5."),
    ],
    10: [
        ("원격 HTTP MCP 서버를 추가하는 명령은?",
         ["claude add-server", "claude mcp add --transport http <name> <url>", "claude connect", "npm install mcp"], 1,
         "`claude mcp add --transport http notion https://mcp.notion.com/mcp` 형태로 추가합니다. sse·stdio 전송도 있습니다."),
        ("팀 전체와 공유(.mcp.json 커밋)하려면 어떤 MCP 스코프를 쓰나요?",
         ["local", "project", "user", "global"], 1,
         "`--scope project`는 `.mcp.json`에 저장되어 커밋을 통해 팀과 공유됩니다. local은 나만, user는 내 모든 프로젝트."),
        ("스킬·훅·서브에이전트·MCP를 한 단위로 묶어 배포하는 것은?",
         ["플러그인", "스킬", "훅", "서브에이전트"], 0,
         "플러그인은 여러 확장을 하나의 설치 단위로 묶습니다. `/plugin`으로 마켓플레이스에서 설치합니다."),
    ],
    12: [
        ("컨텍스트 로트(context rot)란 무엇인가요?",
         ["컨텍스트가 암호화되는 것", "토큰이 많아질수록 정보 회상·집중 능력이 떨어지는 현상", "컨텍스트가 사라지는 버그", "모델이 느려지는 것"], 1,
         "LLM은 유한한 어텐션 예산을 가져, 토큰이 늘수록 정확히 기억·집중하기 어려워집니다. 성능은 절벽이 아니라 완만한 하강."),
        ("1M 토큰 컨텍스트 창을 가능한 한 가득 채우면?",
         ["항상 더 좋은 결과", "오히려 컨텍스트 로트로 성능이 완만히 하강할 수 있음", "비용만 늘고 품질 동일", "속도만 빨라짐"], 1,
         "창을 다 채운다고 좋아지지 않습니다. 목표는 결과 확률을 최대화하는 '가장 작은 고신호 토큰 집합'입니다."),
        ("긴 작업에서 컨텍스트를 관리하는 3대 기법이 아닌 것은?",
         ["압축(compaction)", "구조화 노트/에이전트 기억", "서브에이전트 아키텍처", "모델 파인튜닝"], 3,
         "압축·구조화 노트·서브에이전트가 3대 기법입니다. 이 강의의 /compact·자동기억·서브에이전트가 그 구현입니다."),
    ],
    13: [
        ("에이전트 하네스 공식 \"에이전트 = ___ + 하네스\"의 빈칸은?",
         ["프롬프트", "모델", "도구", "컨텍스트"], 1,
         "'에이전트 = 모델 + 하네스.' 원시 모델은 텍스트만 생성하고, 하네스가 감싸야 자율 에이전트가 됩니다."),
        ("네 가지 엔지니어링 계층의 올바른 순서(기초→고급)는?",
         ["컨텍스트→프롬프트→루프→하네스", "프롬프트→컨텍스트→하네스→루프", "하네스→루프→프롬프트→컨텍스트", "루프→하네스→컨텍스트→프롬프트"], 1,
         "프롬프트→컨텍스트→하네스→루프의 누적 스택입니다. 위 계층은 아래 계층의 약점을 물려받습니다."),
        ("사람 개입 없이 자동 반복하는 '무인 루프'에 반드시 필요한 것은?",
         ["더 큰 모델", "검증(센서) — /goal·테스트 훅·검증 서브에이전트", "더 긴 프롬프트", "더 많은 도구"], 1,
         "'무인 루프는 무인으로 실수하는 루프'이기도 합니다. 검증(센서)이 결정적이며, /goal·Stop 훅·검증 에이전트로 게이트를 겁니다."),
    ],
    14: [
        ("최신 모델(Opus 5 등)에서, 예전 프롬프트의 '최종 검증 단계를 넣어라' 같은 지시는?",
         ["더 강하게 강조한다", "제거하는 것이 개선이다 — 모델이 스스로 검증하므로", "그대로 둔다", "서브에이전트로 옮긴다"], 1,
         "최신 모델은 시키지 않아도 자기 작업을 검증합니다. 검증 강제 지시는 과잉 검증을 유발해 토큰만 낭비하므로 빼는 게 낫습니다."),
        ("Opus 5의 길어진 응답(장황함)을 줄이는 올바른 방법은?",
         ["effort를 낮춘다", "간결하게 하라고 명시적으로 프롬프트한다", "max_tokens를 줄인다", "모델을 바꾼다"], 1,
         "effort는 '얼마나 생각하는지'를 조절할 뿐 응답 길이가 아닙니다. 길이는 명시적 지시로 조절하세요."),
        ("Opus 5에서 thinking을 끄면 생기는 아티팩트(도구호출 텍스트 누수 등)의 최선 완화책은?",
         ["태그 이름을 지목해 금지", "사고를 끄지 말고 effort를 low로 낮춰 비용 통제", "max_tokens를 늘림", "도구를 모두 제거"], 1,
         "대부분 '사고 켜짐 + low effort'가 '사고 꺼짐'보다 낫습니다. 끄면 도구호출·XML 태그 누수가 생깁니다."),
    ],
    16: [
        ("가장 최근 세션을 이어서 여는 방법은?",
         ["claude --new", "claude --continue", "/reset", "claude --fresh"], 1,
         "`claude --continue`는 최근 세션을, `claude --resume`은 목록에서 골라 재개합니다. `/rename`으로 이름을 붙여 두면 찾기 쉽습니다."),
        ("Claude Code를 라이브러리로 패키징해 자체 인프라에서 에이전트를 만드는 것은?",
         ["Claude API", "Claude Agent SDK", "MCP", "번들 스킬"], 1,
         "Claude Agent SDK는 내장 도구·에이전트 루프·훅·서브에이전트를 코드에서 그대로 씁니다. 헤드리스 `-p`는 CLI 자동화용입니다."),
        ("클라우드/웹 세션에서 개인 스킬을 쓰려면?",
         ["아무것도 안 해도 됨", "저장소 `.claude/skills/`에 커밋(또는 플러그인으로 배포)", "설정에서 켜기", "불가능"], 1,
         "클라우드/웹 세션은 로컬 `~/.claude/skills/`를 읽지 않습니다. 저장소에 커밋하거나 플러그인으로 배포해야 합니다."),
    ],
}


def build_quiz(idx):
    items = QUIZZES.get(idx)
    if not items:
        return ""
    qs = []
    for n, (q, opts, ans, expl) in enumerate(items, start=1):
        # 질문·해설은 인라인 코드(`...`)를 <code>로 변환
        q_html = md_inline(q)
        expl_html = md_inline(expl)
        opt_html = "".join(
            f'<button class="quiz-opt" type="button">'
            f'<span class="quiz-mark"></span>{md_inline(o)}</button>'
            for o in opts
        )
        qs.append(
            f'<div class="quiz-q" data-answer="{ans}" data-qid="q{idx}-{n}">'
            f'<p class="quiz-question"><span class="quiz-n">Q{n}.</span> {q_html}</p>'
            f'<div class="quiz-opts">{opt_html}</div>'
            f'<div class="quiz-explain"><b>해설</b> · {expl_html}</div>'
            f'</div>'
        )
    return (
        '<div class="quiz">'
        '<div class="quiz-head">확인 퀴즈'
        '<button class="quiz-retry" type="button" hidden>다시 풀기</button></div>'
        + "".join(qs)
        + '</div>'
    )


def md_inline(text):
    """아주 얕은 인라인 마크다운: `code` 와 **bold** 만 처리 후 이스케이프."""
    # 먼저 이스케이프한 뒤 토큰 복원
    esc = html.escape(text)
    esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)
    esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", esc)
    return esc


def slugify(value, sep="-"):
    value = re.sub(r"[^\w\s가-힣-]", "", value, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s]+", sep, value)


def extract_mermaid(md_text):
    """```mermaid 블록을 플레이스홀더로 치환하고 원문 목록 반환."""
    blocks = []

    def repl(m):
        blocks.append(m.group(1))
        return f"\n\nMERMAIDPLACEHOLDER{len(blocks) - 1}ENDPLACEHOLDER\n\n"

    md_text = re.sub(r"```mermaid\n(.*?)```", repl, md_text, flags=re.DOTALL)
    return md_text, blocks


def reinsert_mermaid(html_text, blocks):
    def repl(m):
        raw = blocks[int(m.group(1))]
        return f'<pre class="mermaid">{html.escape(raw)}</pre>'

    return re.sub(
        r"<p>MERMAIDPLACEHOLDER(\d+)ENDPLACEHOLDER</p>", repl, html_text
    )


def rewrite_links(md_text):
    """인페이지 #앵커 링크 정리.

    - #ch1..#chN(ANCHOR_KEEP), #top 은 실제 챕터 링크로 유지
    - 그 외 #앵커(외부 개념·미존재 heading)는 죽은 링크가 되므로 **굵은 텍스트**로 치환
    """
    def repl(m):
        text, target = m.group(1), m.group(2)
        if target in ANCHOR_KEEP:
            return m.group(0)
        return f"**{text}**"

    # [텍스트](#앵커) 형태만 대상 (http 등 외부 링크는 그대로 둠)
    return re.sub(r"\[([^\]]+)\]\(#([^)]*)\)", repl, md_text)


def prefix_ids(chapter_html, toc_tokens, prefix):
    """헤딩 id 및 페이지내 앵커에 챕터 prefix를 붙여 충돌 방지."""
    # id="x" -> id="prefix-x"
    chapter_html = re.sub(
        r'id="([^"]+)"', lambda m: f'id="{prefix}-{m.group(1)}"', chapter_html
    )
    # href="#x": 챕터 앵커(#chN)·#top 은 그대로, 나머지 헤딩 앵커만 prefix
    def href_repl(m):
        target = m.group(1)
        if target == "top" or re.fullmatch(r"ch\d+", target):
            return m.group(0)
        return f'href="#{prefix}-{target}"'

    chapter_html = re.sub(r'href="#([^"]+)"', href_repl, chapter_html)
    return chapter_html


def walk_toc(tokens, prefix):
    """toc_tokens -> 사이드바 h2 항목 리스트."""
    items = []
    for t in tokens:
        if t["level"] == 2:
            items.append((f"{prefix}-{t['id']}", t["name"]))
    return items


def build():
    chapters_html = []
    sidebar = []

    for i, (fn, title) in enumerate(CHAPTERS, start=1):
        path = os.path.join(SRC, fn)
        with open(path, encoding="utf-8") as f:
            raw = f.read()

        raw = rewrite_links(raw)
        raw, mermaid_blocks = extract_mermaid(raw)

        md = markdown.Markdown(
            extensions=["fenced_code", "tables", "toc", "attr_list"],
            extension_configs={"toc": {"slugify": slugify, "permalink": False}},
        )
        body = md.convert(raw)
        prefix = f"c{i}"
        body = prefix_ids(body, md.toc_tokens, prefix)
        body = reinsert_mermaid(body, mermaid_blocks)

        chapters_html.append(
            f'<section class="chapter" id="ch{i}">'
            f'<div class="ch-badge">CHAPTER {i:02d}</div>'
            f'<h1 class="ch-title">{html.escape(title)}</h1>'
            f'{body}{build_quiz(i)}</section>'
        )

        subitems = walk_toc(md.toc_tokens, prefix)
        sub_html = "".join(
            f'<a class="toc-sub" href="#{sid}">{html.escape(name)}</a>'
            for sid, name in subitems
        )
        caret = '<span class="toc-caret" aria-hidden="true">›</span>' if sub_html else ''
        sidebar.append(
            f'<div class="toc-group{" has-subs" if sub_html else ""}">'
            f'<a class="toc-ch" href="#ch{i}"><span class="toc-num">{i:02d}</span>'
            f'<span class="toc-label">{html.escape(title)}</span>{caret}</a>'
            f'<div class="toc-subs"><div class="toc-subs-inner">{sub_html}</div></div>'
            f'</div>'
        )

    page = (TEMPLATE
            .replace("{{SIDEBAR}}", "\n".join(sidebar))
            .replace("{{CONTENT}}", "\n".join(chapters_html))
            .replace("{{JSONLD}}", build_jsonld()))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Wrote {OUT} ({len(page.encode('utf-8'))} bytes, {len(CHAPTERS)} chapters)")
    write_seo_files()


def build_jsonld():
    """검색엔진용 구조화 데이터. 단일 페이지라 챕터는 hasPart 로만 노출한다
    (존재하지 않는 URL 을 만들어 내지 않는다)."""
    data = {
        "@context": "https://schema.org",
        "@type": "Course",
        "name": SITE_NAME,
        "description": "설치부터 컨텍스트 엔지니어링·하네스까지 — Claude Code 한국어 종합 실전 강의.",
        "url": SITE_URL + "/",
        "inLanguage": "ko",
        "isAccessibleForFree": True,
        "learningResourceType": "Course",
        "teaches": [t for _, t in CHAPTERS],
        "provider": {"@type": "Organization", "name": AUTHOR, "url": SITE_URL + "/"},
        "author": {"@type": "Organization", "name": AUTHOR},
        "license": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "hasCourseInstance": {
            "@type": "CourseInstance",
            "courseMode": "online",
            "courseWorkload": "PT6H",
        },
        "hasPart": [
            {
                "@type": "LearningResource",
                "position": i,
                "name": title,
                "url": f"{SITE_URL}/#ch{i}",
            }
            for i, (_, title) in enumerate(CHAPTERS, start=1)
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def write_seo_files():
    today = datetime.date.today().isoformat()
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url>\n"
        f"    <loc>{SITE_URL}/</loc>\n"
        f"    <lastmod>{today}</lastmod>\n"
        "    <changefreq>weekly</changefreq>\n"
        "    <priority>1.0</priority>\n"
        "  </url>\n"
        "</urlset>\n"
    )
    robots = (
        "User-agent: *\n"
        "Allow: /\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    for name, text in (("sitemap.xml", sitemap), ("robots.txt", robots)):
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            f.write(text)
    print(f"Wrote sitemap.xml, robots.txt (lastmod {today})")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude Code 마스터 클래스 · 한국어 종합 실전 강의</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#0e0f13">
<link rel="canonical" href="https://claude-code-tutorial-ko.vercel.app/">
<script type="application/ld+json">
{{JSONLD}}
</script>
<meta name="description" content="Claude Code 한국어 종합 실전 강의 — 설치·권한·모델·명령어·CLAUDE.md·자동 기억·서브에이전트·스킬·훅·MCP·오케스트레이션.">
<!-- Open Graph / 소셜 미리보기 -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="Claude Code 마스터 클래스">
<meta property="og:url" content="https://claude-code-tutorial-ko.vercel.app/">
<meta property="og:title" content="Claude Code 마스터 클래스">
<meta property="og:description" content="설치부터 루프 엔지니어링까지 — Claude Code 한국어 종합 실전 강의. 17챕터, 각 챕터 확인 퀴즈 포함.">
<meta property="og:image" content="https://claude-code-tutorial-ko.vercel.app/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Claude Code 마스터 클래스 — 한국어 종합 실전 강의">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Claude Code 마스터 클래스">
<meta name="twitter:description" content="설치부터 루프 엔지니어링까지 — Claude Code 한국어 종합 실전 강의. 17챕터, 퀴즈 포함.">
<meta name="twitter:image" content="https://claude-code-tutorial-ko.vercel.app/og.png">
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github-dark.min.css" id="hljs-theme">
<script>
/* FOUC 방지: 저장값 → 없으면 OS 설정(prefers-color-scheme)으로 초기 테마 결정 */
(function(){
  var t;
  try{ t = localStorage.getItem('cc-theme'); }catch(e){}
  if(!t) t = (window.matchMedia && matchMedia('(prefers-color-scheme: light)').matches) ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', t);
  var l = document.getElementById('hljs-theme');
  if(l && t==='light') l.href='https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github.min.css';
})();
</script>
<style>
:root{
  --bg:#0e0f13; --panel:#15171d; --panel2:#1b1e26; --ink:#e7e3da; --ink-dim:#a7a396;
  --line:#2a2d38; --accent:#e07a4b; --accent2:#c9a86a; --code-bg:#1a1d24;
  --sidebar-w:300px; --max:820px;
}
:root[data-theme="light"]{
  --bg:#f4f1ea; --panel:#fbf9f4; --panel2:#efe9dd; --ink:#26241f; --ink-dim:#6b6656;
  --line:#ded7c7; --accent:#c25a2c; --accent2:#a8813a; --code-bg:#f0ebe0;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Apple SD Gothic Neo","Noto Sans KR",sans-serif;
  line-height:1.75;font-size:16.5px;-webkit-font-smoothing:antialiased;overflow-x:hidden}
.content{overflow-wrap:break-word}
.content :not(pre)>code,.quiz-opt code,.quiz-explain code{overflow-wrap:anywhere;word-break:break-word}
.quiz-question,.quiz-opt,.quiz-explain{overflow-wrap:anywhere}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
code,pre,.mono{font-family:"SF Mono",ui-monospace,"JetBrains Mono","D2Coding",Menlo,Consolas,monospace}

/* layout */
.layout{display:flex;min-height:100vh}
.sidebar{width:var(--sidebar-w);flex:0 0 var(--sidebar-w);position:sticky;top:0;height:100vh;
  overflow-y:auto;background:var(--panel);border-right:1px solid var(--line);padding:22px 16px 60px}
.brand{display:flex;align-items:center;gap:10px;padding:8px 10px 18px;border-bottom:1px solid var(--line);margin-bottom:14px}
.brand .dot{width:11px;height:11px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 25%,transparent)}
.brand b{font-size:14.5px;letter-spacing:.2px}
.brand small{display:block;color:var(--ink-dim);font-size:11.5px;font-weight:400;margin-top:2px}
.toc-group{margin-bottom:2px}
.toc-ch{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:9px;color:var(--ink);font-weight:600;font-size:14px;cursor:pointer}
.toc-ch:hover{background:var(--panel2);text-decoration:none}
.toc-ch.active{background:color-mix(in srgb,var(--accent) 16%,transparent);color:var(--accent)}
.toc-num{font-family:"SF Mono",monospace;font-size:11px;color:var(--accent2);min-width:20px}
.toc-ch.active .toc-num{color:var(--accent)}
.toc-label{flex:1;min-width:0}
.toc-caret{color:var(--ink-dim);font-size:17px;line-height:1;transition:transform .2s ease;transform:rotate(0deg);flex:none}
.toc-ch:hover .toc-caret{color:var(--ink)}
.toc-group.open .toc-caret{transform:rotate(90deg);color:var(--accent)}
.toc-subs{display:grid;grid-template-rows:0fr;transition:grid-template-rows .22s ease}
.toc-subs>*{overflow:hidden}
.toc-group.open .toc-subs{grid-template-rows:1fr}
@keyframes tocIn{from{opacity:0}to{opacity:1}}
.toc-sub{display:block;padding:5px 10px 5px 40px;color:var(--ink-dim);font-size:12.8px;border-radius:7px}
.toc-sub:hover{color:var(--ink);text-decoration:none}
.toc-sub.active{color:var(--accent);background:color-mix(in srgb,var(--accent) 10%,transparent)}

/* content */
.main{flex:1;min-width:0;display:flex;justify-content:center;padding:0 32px}
.content{width:100%;max-width:var(--max);padding:56px 0 120px}
#top{margin-bottom:40px}
.hero{background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 14%,var(--panel)),var(--panel));
  border:1px solid var(--line);border-radius:18px;padding:34px 32px}
.hero .kicker{font-family:"SF Mono",monospace;font-size:12px;color:var(--accent2);letter-spacing:1.5px;text-transform:uppercase}
.hero h1{font-size:31px;line-height:1.25;margin:10px 0 12px}
.hero p{color:var(--ink-dim);margin:0 0 6px}
.hero .toc-pills{display:flex;flex-wrap:wrap;gap:7px;margin-top:18px}
.hero .toc-pills span{font-size:12.5px;font-family:"SF Mono",monospace;background:var(--code-bg);
  border:1px solid var(--line);padding:4px 10px;border-radius:20px;color:var(--ink-dim)}

.chapter{padding-top:40px;margin-top:20px;scroll-margin-top:72px}
.chapter+.chapter{border-top:1px solid var(--line)}
/* 화면에서만: 뷰포트 밖 챕터는 렌더링을 건너뛴다(초기 레이아웃 비용 대부분이 여기서 나온다).
   contain-intrinsic-size 의 auto 키워드가 "한 번 렌더한 실제 높이"를 기억하므로,
   아래 폴백 값은 첫 렌더 전 추정치로만 쓰인다. 챕터별 실측값은 tools/prerender.mjs 가
   #cv-sizes 스타일로 덮어쓴다 — 추정 오차가 크면 smooth scroll 이 목표를 빗나간다. */
@media screen{
  .chapter{content-visibility:auto;contain-intrinsic-size:auto 5000px}
}
/* 인쇄는 전부 펼쳐야 한다 — 건너뛴 챕터가 빈 페이지로 나가면 안 된다 */
@media print{
  .chapter{content-visibility:visible;contain-intrinsic-size:none}
}
.ch-badge{font-family:"SF Mono",monospace;font-size:12px;color:var(--accent);letter-spacing:2px}
.ch-title{font-size:27px;margin:6px 0 22px;line-height:1.3}
.content h2{font-size:21px;margin:38px 0 14px;padding-bottom:8px;border-bottom:1px solid var(--line);scroll-margin-top:72px}
.content h3{font-size:17.5px;margin:26px 0 10px;color:var(--ink);scroll-margin-top:72px}
.content h4{font-size:15.5px;margin:20px 0 8px;color:var(--accent2)}
.content p{margin:12px 0}
.content ul,.content ol{padding-left:24px;margin:12px 0}
.content li{margin:6px 0}
.content strong{color:var(--ink);font-weight:700}
.content blockquote{margin:16px 0;padding:10px 18px;border-left:3px solid var(--accent);
  background:var(--panel);border-radius:0 10px 10px 0;color:var(--ink-dim)}
.content hr{border:0;border-top:1px solid var(--line);margin:30px 0}
.content img{max-width:100%;border-radius:10px}

/* code */
.content :not(pre)>code{background:var(--code-bg);border:1px solid var(--line);
  padding:1.5px 6px;border-radius:6px;font-size:.87em;color:var(--accent2)}
.content pre{background:var(--code-bg);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;overflow-x:auto;margin:16px 0;font-size:13.5px;line-height:1.6}
.content pre code{background:none;border:0;padding:0;color:var(--ink)}
pre.mermaid{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:20px;text-align:center;overflow-x:auto}
/* 빌드 시점에 미리 렌더된 도표 (tools/prerender.mjs) — 테마별 두 벌을 넣고 CSS로 전환 */
.mmd{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:20px;text-align:center;overflow-x:auto;margin:16px 0}
figure.mmd{margin-left:0;margin-right:0}
.mmd svg{max-width:100%;height:auto;display:block;margin:0 auto}
:root[data-theme="dark"] .mmd-light{display:none}
:root[data-theme="light"] .mmd-dark{display:none}

/* tables */
.content table{border-collapse:collapse;width:100%;margin:16px 0;font-size:14px;display:block;overflow-x:auto}
.content th,.content td{border:1px solid var(--line);padding:9px 12px;text-align:left}
.content th{background:var(--panel2);font-weight:600}

/* quiz */
.quiz{margin:40px 0 8px;padding:22px 22px 8px;border:1px solid var(--line);border-radius:16px;
  background:linear-gradient(180deg,color-mix(in srgb,var(--accent2) 8%,var(--panel)),var(--panel))}
.quiz-head{display:flex;align-items:center;gap:8px;font-weight:700;font-size:15px;margin-bottom:4px;color:var(--accent2)}
.quiz-retry{margin-left:auto;font:inherit;font-size:12px;font-weight:600;cursor:pointer;
  background:var(--panel2);border:1px solid var(--line);color:var(--ink-dim);border-radius:8px;padding:4px 11px}
.quiz-retry:hover{border-color:var(--accent);color:var(--accent)}
.quiz-retry[hidden]{display:none}
.quiz-head::before{content:"✏️";font-size:16px}
.quiz-q{padding:16px 0;border-top:1px solid var(--line)}
.quiz-q:first-of-type{border-top:0}
.quiz-question{margin:0 0 12px;font-weight:600;line-height:1.6}
.quiz-n{color:var(--accent);font-family:"SF Mono",monospace;margin-right:4px}
.quiz-opts{display:flex;flex-direction:column;gap:8px}
.quiz-opt{display:flex;align-items:center;gap:10px;width:100%;text-align:left;cursor:pointer;
  background:var(--panel2);border:1px solid var(--line);color:var(--ink);
  padding:11px 14px;border-radius:10px;font:inherit;font-size:14.5px;transition:.15s}
.quiz-opt:hover{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 8%,var(--panel2))}
.quiz-opt code{background:color-mix(in srgb,var(--ink) 8%,transparent);padding:1px 5px;border-radius:5px;font-size:.9em}
.quiz-mark{flex:0 0 18px;width:18px;height:18px;border:2px solid var(--line);border-radius:50%;display:inline-block}
.quiz-q.answered .quiz-opt{cursor:default}
.quiz-q.answered .quiz-opt:hover{border-color:var(--line);background:var(--panel2)}
.quiz-opt.correct{border-color:#3aa76d;background:color-mix(in srgb,#3aa76d 16%,var(--panel2))}
.quiz-opt.correct .quiz-mark{border-color:#3aa76d;background:#3aa76d;position:relative}
.quiz-opt.correct .quiz-mark::after{content:"✓";position:absolute;inset:0;color:#fff;font-size:12px;line-height:15px;text-align:center;font-weight:700}
.quiz-opt.wrong{border-color:#d05a4e;background:color-mix(in srgb,#d05a4e 14%,var(--panel2))}
.quiz-opt.wrong .quiz-mark{border-color:#d05a4e;background:#d05a4e;position:relative}
.quiz-opt.wrong .quiz-mark::after{content:"✕";position:absolute;inset:0;color:#fff;font-size:11px;line-height:15px;text-align:center;font-weight:700}
.quiz-explain{display:none;margin-top:12px;padding:11px 14px;border-radius:10px;font-size:14px;line-height:1.65;
  background:var(--code-bg);border:1px solid var(--line);color:var(--ink-dim)}
.quiz-explain b{color:var(--accent2)}
.quiz-q.answered .quiz-explain{display:block}

/* footer */
.site-footer{margin-top:56px;padding:28px 24px 8px;border-top:1px solid var(--line);
  display:flex;flex-direction:column;align-items:center;gap:16px;text-align:center}
.site-footer .credit{font-size:14px;color:var(--ink-dim);letter-spacing:.3px}
.site-footer .credit b{color:var(--accent2);font-family:"SF Mono",ui-monospace,Menlo,monospace;font-weight:700}
.site-footer .foot-links{display:flex;flex-wrap:wrap;gap:12px;justify-content:center}
.site-footer .foot-links a{display:inline-flex;align-items:center;gap:6px;font-size:14px;font-weight:600;
  color:var(--ink);text-decoration:none;background:var(--panel2);border:1px solid var(--line);
  padding:10px 16px;border-radius:11px;transition:.15s}
.site-footer .foot-links a:hover{border-color:var(--accent);color:var(--accent);
  background:color-mix(in srgb,var(--accent) 9%,var(--panel2))}

/* 코드 복사 버튼 */
.content pre{position:relative}
.copy-btn{position:absolute;top:8px;right:8px;font:inherit;font-size:11.5px;cursor:pointer;
  background:var(--panel);color:var(--ink-dim);border:1px solid var(--line);border-radius:7px;
  padding:4px 9px;opacity:0;transition:.15s;z-index:2}
.content pre:hover .copy-btn,.copy-btn:focus{opacity:1}
.copy-btn:hover{color:var(--accent);border-color:var(--accent)}
.copy-btn.done{color:#3aa76d;border-color:#3aa76d;opacity:1}
pre.mermaid .copy-btn{display:none}

/* 사이드바 검색·진도 */
.search-trigger{display:flex;align-items:center;gap:9px;margin:0 10px 12px;padding:9px 12px;
  background:var(--panel2);border:1px solid var(--line);border-radius:10px;color:var(--ink-dim);
  font:inherit;font-size:13px;cursor:pointer;width:calc(100% - 20px)}
.search-trigger:hover{border-color:var(--accent);color:var(--ink)}
.search-trigger kbd{margin-left:auto;font-family:"SF Mono",monospace;font-size:10.5px;
  background:var(--bg);border:1px solid var(--line);border-radius:4px;padding:1px 6px}
.read-progress{margin:0 12px 14px;font-size:11.5px;color:var(--ink-dim);display:flex;flex-direction:column;gap:5px}
.read-progress .rp-top{display:flex;align-items:center;gap:8px}
.rp-reset{margin-left:auto;font:inherit;font-size:10.5px;cursor:pointer;background:transparent;
  border:1px solid var(--line);color:var(--ink-dim);border-radius:6px;padding:2px 7px;white-space:nowrap}
.rp-reset:hover{border-color:var(--accent);color:var(--accent)}
.read-progress .rbar{height:5px;border-radius:3px;background:var(--panel2);overflow:hidden}
.read-progress .rbar i{display:block;height:100%;width:0;transition:width .5s ease;
  background:linear-gradient(90deg,var(--accent),var(--accent2))}
.toc-ch.done .toc-label::after{content:"✓";color:#3aa76d;font-size:12px;font-weight:700;margin-left:7px}

/* 검색 모달 */
.search-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:60;display:none;
  align-items:flex-start;justify-content:center;padding-top:11vh}
.search-backdrop.open{display:flex}
.search-box{width:min(560px,92vw);background:var(--panel);border:1px solid var(--line);border-radius:14px;
  overflow:hidden;box-shadow:0 24px 60px rgba(0,0,0,.5)}
.search-box input{width:100%;box-sizing:border-box;padding:16px 18px;font:inherit;font-size:16px;
  background:transparent;border:0;border-bottom:1px solid var(--line);color:var(--ink);outline:none}
.search-results{max-height:52vh;overflow-y:auto}
.search-results a{display:flex;gap:11px;align-items:baseline;padding:11px 18px;color:var(--ink);
  text-decoration:none;font-size:14.5px;border-bottom:1px solid var(--line)}
.search-results a:last-child{border-bottom:0}
.search-results a.sel,.search-results a:hover{background:color-mix(in srgb,var(--accent) 13%,var(--panel))}
.search-results .r-num{font-family:"SF Mono",monospace;font-size:11px;color:var(--accent2);min-width:30px}
.search-results .r-sub{color:var(--ink-dim);font-size:12px;margin-left:6px}
.search-results a>span:nth-child(2){min-width:0;flex:1}
.search-results .r-title{overflow-wrap:anywhere}
.search-results .r-snip{display:block;color:var(--ink-dim);font-size:12.5px;line-height:1.55;margin-top:3px;
  overflow-wrap:anywhere;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.search-results mark{background:color-mix(in srgb,var(--accent) 34%,transparent);color:var(--ink);
  border-radius:3px;padding:0 2px}
.search-count{padding:7px 18px;font-size:11px;color:var(--ink-dim);border-bottom:1px solid var(--line)}
/* 검색 결과로 이동했을 때 잠깐 강조 */
@keyframes hitflash{0%,60%{background:color-mix(in srgb,var(--accent) 20%,transparent)}100%{background:transparent}}
.hit-flash{animation:hitflash 1.5s ease-out;border-radius:6px}
.search-empty{padding:22px;text-align:center;color:var(--ink-dim);font-size:14px}
.search-hint{padding:9px 18px;font-size:11px;color:var(--ink-dim);border-top:1px solid var(--line);display:flex;gap:16px}
.search-hint kbd{font-family:"SF Mono",monospace;background:var(--panel2);border:1px solid var(--line);border-radius:4px;padding:1px 5px;margin-right:2px}

/* 퀴즈 점수 칩 */
#quizStat{position:fixed;bottom:18px;right:18px;z-index:45;font-size:13px;font-weight:600;
  background:var(--panel);border:1px solid var(--line);color:var(--ink);border-radius:22px;
  padding:9px 16px;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.32);display:none;gap:7px}
#quizStat:hover{border-color:var(--accent);color:var(--accent)}

/* 수료증 */
.cert-form{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:6px}
.cert-form input{flex:1;min-width:180px;padding:11px 14px;font:inherit;font-size:15px;background:var(--code-bg);
  border:1px solid var(--line);border-radius:10px;color:var(--ink);outline:none}
.cert-form input:focus{border-color:var(--accent)}
.cert-btn{padding:11px 18px;font:inherit;font-weight:700;font-size:14px;cursor:pointer;border-radius:10px;
  background:var(--accent);color:#0e0f13;border:0}
.cert-btn.ghost{background:var(--panel2);color:var(--ink);border:1px solid var(--line);display:none}
.cert-btn:hover{filter:brightness(1.06)}
#certCanvas{max-width:100%;height:auto;margin-top:16px;border:1px solid var(--line);border-radius:12px;display:none}
.cert-stat{margin-top:10px;font-size:13px;color:var(--ink-dim)}
.cert-stat b{color:var(--accent2)}
.cert-note{display:none;margin-top:12px;padding:11px 14px;font-size:13px;line-height:1.6;color:var(--ink-dim);
  background:var(--code-bg);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:9px}
.cert-note b{color:var(--ink)}

/* 플레이그라운드 — 터미널 */
.pg-terminal{background:#0b0c10;border:1px solid var(--line);border-radius:12px;overflow:hidden;font-family:"SF Mono",ui-monospace,Menlo,monospace}
.pg-bar{display:flex;align-items:center;padding:9px 13px;background:var(--panel2);border-bottom:1px solid var(--line)}
.pg-bar i{width:11px;height:11px;border-radius:50%;margin-right:7px;display:inline-block}
.pg-bar i:nth-child(1){background:#e0574e}.pg-bar i:nth-child(2){background:#c9a86a}.pg-bar i:nth-child(3){background:#3aa76d}
.pg-bar span{margin-left:6px;font-size:12px;color:var(--ink-dim)}
.pg-out{padding:14px 16px;height:280px;overflow-y:auto;font-size:13.5px;line-height:1.7;color:#f2efe8}
.pg-out .u{color:#e07a4b}.pg-out .sys{color:#a7a396}.pg-out .ok{color:#4cc189}.pg-out .err{color:#f07a6f}.pg-out .k{color:#d9b775}
.pg-inline{display:flex;align-items:center;gap:9px;padding:11px 16px;border-top:1px solid var(--line);background:#0e0f13}
.pg-inline .p{color:#e07a4b;font-weight:700}
.pg-inline input{flex:1;background:transparent;border:0;outline:none;color:#fff;font:inherit;font-size:14px;caret-color:#e07a4b}
.pg-inline input::placeholder{color:#6f6c63}
.pg-chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:10px}
.pg-chips button{font-family:"SF Mono",monospace;font-size:12px;cursor:pointer;background:var(--panel2);border:1px solid var(--line);color:var(--ink-dim);border-radius:20px;padding:5px 12px}
.pg-chips button:hover{border-color:var(--accent);color:var(--accent)}

/* 플레이그라운드 — 위저드 */
.pg-wizard{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px}
.pg-q{font-weight:700;font-size:15.5px;margin-bottom:14px}
.pg-opts{display:flex;flex-direction:column;gap:9px}
.pg-opts button{text-align:left;font:inherit;font-size:14px;cursor:pointer;background:var(--panel2);
  border:1px solid var(--line);color:var(--ink);border-radius:10px;padding:12px 15px;transition:.15s}
.pg-opts button:hover{border-color:var(--accent);background:color-mix(in srgb,var(--accent) 8%,var(--panel2))}
.pg-result .tag{display:inline-block;font-family:"SF Mono",monospace;font-size:12px;color:var(--accent2);letter-spacing:1px;margin-bottom:8px}
.pg-result h4{font-size:22px;margin:0 0 8px;color:var(--accent)}
.pg-result p{color:var(--ink-dim);font-size:14px;margin:0 0 12px;line-height:1.6}
.pg-result strong{color:var(--ink)}
.pg-result a{font-weight:600}
.pg-again{margin-top:12px;font:inherit;font-size:13px;cursor:pointer;background:transparent;border:1px solid var(--line);color:var(--ink-dim);border-radius:9px;padding:8px 14px}
.pg-again:hover{border-color:var(--accent);color:var(--accent)}

/* 플레이그라운드 — 계산기 */
.pg-cost{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px}
.pg-cost .presets{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px}
.pg-cost .presets button{font:inherit;font-size:13px;cursor:pointer;background:var(--panel2);border:1px solid var(--line);color:var(--ink);border-radius:20px;padding:7px 14px;transition:.15s}
.pg-cost .presets button:hover,.pg-cost .presets button.on{border-color:var(--accent);color:var(--accent);background:color-mix(in srgb,var(--accent) 9%,var(--panel2))}
.pg-cost .fld{margin-bottom:17px}
.pg-cost .fld .lab{display:flex;justify-content:space-between;align-items:baseline;gap:10px;font-size:13.5px;color:var(--ink-dim);margin-bottom:8px}
.pg-cost .fld .lab b{color:var(--ink);font-weight:600}
.pg-cost .fld .val{color:var(--accent2);font-weight:700;font-family:"SF Mono",monospace;font-size:13px;white-space:nowrap}
.pg-cost select{width:100%;font:inherit;font-size:14px;padding:10px 12px;background:var(--code-bg);border:1px solid var(--line);border-radius:9px;color:var(--ink);outline:none}
.pg-cost input[type=range]{width:100%;height:6px;accent-color:var(--accent);cursor:pointer}
.pg-cost select:focus{border-color:var(--accent)}
.pg-cost .out{margin-top:4px;padding:20px;background:var(--code-bg);border:1px solid var(--line);border-radius:12px;text-align:center}
.pg-cost .out .krw{font-size:40px;font-weight:800;color:var(--accent);font-family:"SF Mono",monospace;line-height:1.1}
.pg-cost .out .usd{font-size:14px;color:var(--ink-dim);margin-top:5px;font-family:"SF Mono",monospace}
.pg-cost .out .brk{font-size:13.5px;color:var(--ink);margin-top:13px;line-height:1.65}
.pg-cost .out .brk b{color:var(--accent2)}
.pg-cost .out .note{font-size:12px;color:var(--ink-dim);margin-top:9px;line-height:1.5}

/* 약관·개인정보·저장소 설정 모달 */
.legal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:70;display:none;
  align-items:center;justify-content:center;padding:20px}
.legal-backdrop.open{display:flex}
.legal-box{width:min(760px,100%);max-height:86vh;display:flex;flex-direction:column;
  background:var(--panel);border:1px solid var(--line);border-radius:16px;overflow:hidden;
  box-shadow:0 30px 90px rgba(0,0,0,.5)}
.legal-head{display:flex;align-items:center;gap:12px;padding:16px 20px;border-bottom:1px solid var(--line);background:var(--panel2)}
.legal-head h2{margin:0;font-size:17px;flex:1}
.legal-head .lg-close{background:transparent;border:1px solid var(--line);color:var(--ink-dim);
  width:32px;height:32px;border-radius:8px;cursor:pointer;font-size:15px;line-height:1}
.legal-head .lg-close:hover{border-color:var(--accent);color:var(--accent)}
.legal-tabs{display:flex;gap:6px;padding:12px 20px 0;flex-wrap:wrap}
.legal-tabs button{font:inherit;font-size:13px;font-weight:600;cursor:pointer;background:transparent;
  border:1px solid var(--line);color:var(--ink-dim);border-radius:20px;padding:6px 14px}
.legal-tabs button.on{border-color:var(--accent);color:var(--accent);background:color-mix(in srgb,var(--accent) 10%,transparent)}
.legal-body{padding:18px 22px 24px;overflow-y:auto;font-size:14.5px;line-height:1.8;color:var(--ink)}
.legal-body h3{font-size:15.5px;margin:22px 0 8px;color:var(--accent2)}
.legal-body h3:first-child{margin-top:4px}
.legal-body p{margin:0 0 10px;color:var(--ink-dim)}
.legal-body ul{margin:0 0 12px;padding-left:20px;color:var(--ink-dim)}
.legal-body li{margin-bottom:5px}
.legal-body b{color:var(--ink)}
.legal-body code{background:var(--code-bg);border:1px solid var(--line);border-radius:5px;
  padding:1px 5px;font-family:"SF Mono",ui-monospace,Menlo,monospace;font-size:12.5px;overflow-wrap:anywhere}
.legal-body table{width:100%;border-collapse:collapse;margin:6px 0 14px;font-size:13px;display:block;overflow-x:auto}
.legal-body th,.legal-body td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
.legal-body th{background:var(--panel2);color:var(--ink);font-weight:600;white-space:nowrap}
.legal-body td{color:var(--ink-dim)}
.legal-meta{font-size:12.5px;color:var(--ink-dim);border-top:1px solid var(--line);margin-top:20px;padding-top:12px}
.legal-note{background:var(--code-bg);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:9px;padding:12px 15px;margin:0 0 16px;font-size:13.5px;line-height:1.7;color:var(--ink-dim)}
.legal-note b{color:var(--accent2)}

/* 저장소 설정 스위치 */
.sw-row{display:flex;align-items:flex-start;gap:14px;padding:14px 0;border-bottom:1px solid var(--line)}
.sw-row:last-of-type{border-bottom:0}
.sw-txt{flex:1;min-width:0}
.sw-txt b{display:block;font-size:14.5px;margin-bottom:3px;color:var(--ink)}
.sw-txt span{font-size:13px;color:var(--ink-dim);line-height:1.6}
.sw-txt code{font-size:12px}
.sw{flex:0 0 46px;width:46px;height:26px;border-radius:99px;border:1px solid var(--line);
  background:var(--panel2);position:relative;cursor:pointer;transition:.18s;margin-top:2px}
.sw::after{content:"";position:absolute;top:2px;left:2px;width:20px;height:20px;border-radius:50%;
  background:var(--ink-dim);transition:.18s}
.sw[aria-checked="true"]{background:color-mix(in srgb,var(--accent) 32%,var(--panel2));border-color:var(--accent)}
.sw[aria-checked="true"]::after{left:22px;background:var(--accent)}
.sw-required{flex:0 0 auto;font-size:11.5px;color:var(--ink-dim);border:1px solid var(--line);
  border-radius:20px;padding:4px 10px;margin-top:4px;white-space:nowrap}
.legal-actions{display:flex;flex-wrap:wrap;gap:9px;margin-top:20px}
.legal-actions button{font:inherit;font-size:13.5px;font-weight:600;cursor:pointer;border-radius:10px;padding:10px 16px;
  background:var(--panel2);border:1px solid var(--line);color:var(--ink)}
.legal-actions button:hover{border-color:var(--accent);color:var(--accent)}
.legal-actions button.danger:hover{border-color:#d05a4e;color:#d05a4e}
.sw-state{font-size:12.5px;color:var(--ink-dim);margin-top:14px;padding-top:12px;border-top:1px solid var(--line)}

/* 최초 방문 안내 배너 */
.consent{position:fixed;left:0;right:0;bottom:0;z-index:65;display:none;justify-content:center;padding:14px}
.consent.show{display:flex}
.consent-in{width:min(880px,100%);display:flex;align-items:center;gap:16px;flex-wrap:wrap;
  background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px 20px;
  box-shadow:0 18px 50px rgba(0,0,0,.42)}
.consent-in p{margin:0;flex:1;min-width:240px;font-size:13.5px;line-height:1.7;color:var(--ink-dim)}
.consent-in p b{color:var(--ink)}
.consent-btns{display:flex;gap:8px;flex-wrap:wrap}
.consent-btns button{font:inherit;font-size:13.5px;font-weight:600;cursor:pointer;border-radius:10px;padding:9px 18px;
  background:var(--panel2);border:1px solid var(--line);color:var(--ink)}
.consent-btns button.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.consent-btns button:hover{border-color:var(--accent);color:var(--accent)}
.consent-btns button.primary:hover{color:#fff;filter:brightness(1.08)}

/* 푸터 법적 고지 */
.site-footer .foot-legal{display:flex;flex-wrap:wrap;gap:8px;justify-content:center}
.site-footer .foot-legal button{font:inherit;font-size:13px;cursor:pointer;background:transparent;
  border:1px solid var(--line);color:var(--ink-dim);border-radius:9px;padding:7px 13px}
.site-footer .foot-legal button:hover{border-color:var(--accent);color:var(--accent)}
.site-footer .disclaimer{font-size:12px;color:var(--ink-dim);line-height:1.7;max-width:640px;opacity:.9}

/* 인쇄 · PDF 저장 — 본문만 남기고 흑백 지면에 맞춘다 */
@media print{
  .sidebar,.topbar,.backdrop,.progress,.theme-toggle,#quizStat,.consent,
  .legal-backdrop,.search-backdrop,.copy-btn,.quiz-retry,.rp-reset,
  .skip-link,.cert-app,.pg-terminal,.pg-wizard,.pg-cost,.site-footer .foot-links{display:none !important}
  :root,:root[data-theme="dark"],:root[data-theme="light"]{
    --bg:#fff;--panel:#fff;--panel2:#fafafa;--ink:#111;--ink-dim:#444;
    --line:#bbb;--accent:#444;--accent2:#666;--code-bg:#f6f6f6}
  html,body{background:#fff !important;color:#111 !important;font-size:10.5pt}
  .layout{display:block}
  .main{padding:0}
  .content{max-width:100%;padding:0}
  .chapter{page-break-before:always;break-before:page}
  .chapter:first-of-type{page-break-before:auto;break-before:auto}
  .ch-title,.content h2,.content h3{page-break-after:avoid;break-after:avoid}
  pre,table,figure.mmd,.quiz-q,blockquote{page-break-inside:avoid;break-inside:avoid}
  pre{white-space:pre-wrap;word-break:break-word;border:1px solid #ccc}
  a{color:#111;text-decoration:underline}
  /* 화면에선 필요 없지만 종이에선 링크 주소가 사라지므로 붙여 준다 */
  .content a[href^="http"]::after{content:" (" attr(href) ")";font-size:9pt;color:#555;word-break:break-all}
  .mmd-dark{display:none !important}
  .mmd-light{display:block !important}
  figure.mmd{border:1px solid #ccc;background:#fff}
  .quiz{border:1px solid #999;background:#fff}
  .quiz-explain{display:block !important}   /* 지면에선 해설을 항상 보여 준다 */
  .quiz-opt{border:1px solid #ccc}
  @page{margin:16mm 14mm}
}

/* topbar (mobile) */
.topbar{display:none;position:sticky;top:0;z-index:30;background:var(--panel);
  border-bottom:1px solid var(--line);padding:10px 14px;align-items:center;gap:12px}
.topbar b{font-size:14px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.icon-btn{background:var(--panel2);border:1px solid var(--line);color:var(--ink);
  width:38px;height:38px;border-radius:9px;cursor:pointer;font-size:16px;display:grid;place-items:center}
.theme-toggle{position:fixed;top:16px;right:20px;z-index:40}

/* progress */
.progress{position:fixed;top:0;left:0;height:3px;background:var(--accent);z-index:50;width:0}

/* 접근성 — 키보드 사용자용 본문 바로가기 · 포커스 링 */
.skip-link{position:absolute;left:-9999px;top:0;z-index:100;background:var(--accent);color:#fff;
  padding:11px 18px;border-radius:0 0 10px 0;font-weight:700;text-decoration:none}
.skip-link:focus{left:0}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}

@media(max-width:900px){
  .sidebar{position:fixed;left:0;top:0;z-index:35;transform:translateX(-100%);transition:transform .25s ease;box-shadow:0 0 40px rgba(0,0,0,.4)}
  body.nav-open .sidebar{transform:translateX(0)}
  .topbar{display:flex}
  .main{padding:0 18px}
  .content{padding:28px 0 100px}
  /* 떠 있는 테마 버튼은 상단바의 검색 버튼과 같은 자리에 겹친다 → 모바일에서는 숨기고
     상단바 안의 #themeBtnM 을 쓴다 */
  .theme-toggle{display:none}
  .hero h1{font-size:25px}
  .backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:34}
  body.nav-open .backdrop{display:block}
}
</style>
</head>
<body>
<a class="skip-link" href="#top">본문으로 건너뛰기</a>
<div class="progress" id="progress"></div>
<div class="topbar">
  <button class="icon-btn" id="menuBtn" aria-label="목차">☰</button>
  <b>Claude Code 마스터 클래스</b>
  <button class="icon-btn" id="searchBtnM" aria-label="검색" style="margin-left:auto">🔍</button>
  <button class="icon-btn" id="themeBtnM" aria-label="테마 전환">◐</button>
</div>
<div class="backdrop" id="backdrop"></div>
<div class="search-backdrop" id="searchModal">
  <div class="search-box">
    <input id="searchInput" type="text" placeholder="본문까지 전체 검색 — 예: PreToolUse, allowed-tools" autocomplete="off" spellcheck="false">
    <div class="search-results" id="searchResults"></div>
    <div class="search-hint"><span><kbd>↑</kbd><kbd>↓</kbd> 이동</span><span><kbd>Enter</kbd> 열기</span><span><kbd>Esc</kbd> 닫기</span></div>
  </div>
</div>
<div id="quizStat" title="수료증으로 이동"></div>

<!-- 이용약관 · 개인정보처리방침 · 저장소 설정 -->
<div class="legal-backdrop" id="legalModal" role="dialog" aria-modal="true" aria-labelledby="legalTitle">
  <div class="legal-box">
    <div class="legal-head">
      <h2 id="legalTitle">이용약관</h2>
      <button class="lg-close" type="button" id="legalClose" aria-label="닫기">✕</button>
    </div>
    <div class="legal-tabs">
      <button type="button" data-tab="terms">이용약관</button>
      <button type="button" data-tab="privacy">개인정보처리방침</button>
      <button type="button" data-tab="storage">저장소 설정</button>
    </div>

    <div class="legal-body" id="legalBody">
      <!-- 이용약관 -->
      <div class="legal-pane" data-pane="terms">
        <div class="legal-note"><b>요약</b> — 무료 학습 자료입니다. 회원가입·결제가 없고, 개인정보를 수집하지 않습니다.
          Anthropic 공식 자료가 아니며, 실제 설정을 적용하기 전에는 공식 문서로 한 번 더 확인하시기 바랍니다.</div>

        <h3>제1조 (목적)</h3>
        <p>본 약관은 AI_Innovation_Studio(이하 “제작자”)가 제공하는 웹 학습 자료 <b>Claude Code 마스터 클래스</b>(이하 “본 사이트”)의
          이용 조건과 제작자·이용자의 권리·의무를 정하는 것을 목적으로 합니다.</p>

        <h3>제2조 (서비스의 성격)</h3>
        <ul>
          <li>본 사이트는 <b>무료로 제공되는 정적 웹 학습 자료</b>입니다.</li>
          <li>회원가입·로그인·결제 기능이 없으며, 이용자를 식별하거나 계정을 생성하지 않습니다.</li>
          <li>별도의 절차 없이 본 사이트에 접속해 이용하는 시점에 본 약관에 동의한 것으로 봅니다.</li>
        </ul>

        <h3>제3조 (비공식 자료 고지)</h3>
        <ul>
          <li>본 사이트는 공개된 공식 문서와 기술 자료를 참고하여 제작자가 별도로 집필한 <b>제3자 학습 자료</b>입니다.</li>
          <li>제작자는 Anthropic PBC와 <b>제휴·후원·승인 관계가 없습니다.</b></li>
          <li>Claude, Claude Code 등 본문에 등장하는 상표와 인용된 문서의 권리는 각 권리자에게 귀속됩니다.</li>
        </ul>

        <h3>제4조 (콘텐츠의 정확성과 한계)</h3>
        <ul>
          <li>본 사이트의 내용은 <b>집필 시점을 기준</b>으로 합니다. 모델 라인업·가격·명령어·설정 형식 등은 수시로 변경될 수 있습니다.</li>
          <li>제작자는 내용의 최신성·정확성·완전성을 보증하지 않습니다.</li>
          <li>실제 업무 환경에 적용하기 전에는 반드시 각 도구의 <b>공식 문서로 확인</b>하시기 바랍니다.</li>
          <li>본문의 비용 계산기·터미널 놀이터 등은 <b>학습용 시뮬레이터</b>이며 실제 요금이나 실행 결과와 다를 수 있습니다.</li>
        </ul>

        <h3>제5조 (저작권 및 이용 범위)</h3>
        <ul>
          <li>본 사이트의 글·구성·디자인에 대한 저작권은 제작자에게 있습니다.</li>
          <li>개인적인 학습 목적의 열람과 출처를 밝힌 인용은 자유롭게 하실 수 있습니다.</li>
          <li>제작자의 사전 동의 없는 <b>전부 또는 상당 부분의 복제·재배포·2차적 저작물 작성·상업적 이용</b>은 금지됩니다.</li>
        </ul>

        <h3>제6조 (이용자의 의무)</h3>
        <ul>
          <li>본 사이트의 정상적인 운영을 방해하는 행위(과도한 자동 요청, 취약점 탐색 등)를 하여서는 안 됩니다.</li>
          <li>본 사이트를 통해 알게 된 설정을 적용할 때에는 관련 법령과 소속 조직의 정책을 준수하여야 합니다.</li>
        </ul>

        <h3>제7조 (외부 링크)</h3>
        <p>본 사이트는 공식 문서·오픈소스 저장소 등 외부 사이트로 연결되는 링크를 포함합니다.
          제작자는 해당 외부 사이트의 내용·정책·안전성에 대해 관리하지 않으며 책임을 지지 않습니다.</p>

        <h3>제8조 (책임의 제한)</h3>
        <ul>
          <li>본 사이트는 무료로 “있는 그대로” 제공되며, 특정 목적에의 적합성을 보증하지 않습니다.</li>
          <li>본 사이트의 내용을 적용하는 과정에서 발생한 <b>설정 오류, 데이터 손실, 비용 발생, 업무상 손해</b>에 대하여
            제작자는 고의 또는 중대한 과실이 없는 한 책임을 지지 않습니다.</li>
          <li>특히 <b>훅(Hooks), 권한 모드, 자동화 루프</b>와 관련된 설정은 이용자의 컴퓨터에서 실제 명령을 실행할 수 있습니다.
            반드시 내용을 이해하고 <b>이용자 본인의 책임 하에</b> 검증한 뒤 적용하시기 바랍니다.</li>
        </ul>

        <h3>제9조 (서비스의 변경·중단)</h3>
        <p>제작자는 사전 통지 없이 본 사이트의 내용을 수정하거나 제공을 중단할 수 있습니다.</p>

        <h3>제10조 (약관의 변경)</h3>
        <p>본 약관이 변경되는 경우 본 사이트에 게시하는 방법으로 공지하며, 게시 시점부터 효력이 발생합니다.</p>

        <h3>제11조 (준거법)</h3>
        <p>본 약관은 대한민국 법을 준거법으로 하며, 분쟁이 발생한 경우 관련 법령이 정한 절차에 따릅니다.</p>

        <div class="legal-meta">시행일: 2026년 7월 26일 · 문의: 페이지 하단의 텔레그램 채널 또는 오픈채팅</div>
      </div>

      <!-- 개인정보처리방침 -->
      <div class="legal-pane" data-pane="privacy" hidden>
        <div class="legal-note"><b>한 줄 요약</b> — 본 사이트는 <b>쿠키를 사용하지 않고</b>, 개인정보를 수집·저장·전송하지 않습니다.
          학습 진도 등 일부 정보는 <b>이용자의 브라우저 안에만</b> 저장되며 서버로 전송되지 않습니다.</div>

        <h3>1. 수집하지 않는 정보</h3>
        <p>본 사이트에는 회원가입·로그인·문의 폼 등 개인정보를 입력받는 기능이 없습니다. 제작자는 다음을 수집하지 않습니다.</p>
        <ul>
          <li>이름·이메일·전화번호 등 신원 정보</li>
          <li>계정 정보 및 결제 정보</li>
          <li>행태정보 수집을 위한 <b>쿠키·광고 식별자·분석 스크립트</b>(Google Analytics 등 일절 사용하지 않습니다)</li>
        </ul>

        <h3>2. 브라우저에 저장되는 항목</h3>
        <p>학습 편의를 위해 아래 항목을 이용자 브라우저의 로컬 저장소(localStorage)에 저장합니다.
          이 값들은 <b>이용자의 기기를 벗어나지 않으며</b>, 제작자를 포함한 누구에게도 전송되지 않습니다.</p>
        <table>
          <tr><th>저장 이름</th><th>내용</th><th>목적</th><th>보관 기간</th></tr>
          <tr><td><code>cc-theme</code></td><td>밝은 테마 / 어두운 테마 선택값</td><td>재방문 시 화면 유지</td><td>삭제 전까지</td></tr>
          <tr><td><code>cc_read</code></td><td>읽은 챕터 번호 목록</td><td>완주 진도 표시</td><td>삭제 전까지</td></tr>
          <tr><td><code>cc_quiz</code></td><td>퀴즈 문항별 선택한 보기 번호</td><td>정답 표시·점수·수료증</td><td>삭제 전까지</td></tr>
          <tr><td><code>cc_prefs</code></td><td>아래 저장소 설정값</td><td>이용자의 선택을 기억하기 위한 필수 항목</td><td>삭제 전까지</td></tr>
        </table>

        <h3>3. 수료증 기능</h3>
        <p>수료증에 입력한 이름은 브라우저 안에서 이미지를 그리는 데에만 사용되며,
          <b>저장하지도 전송하지도 않습니다.</b> 페이지를 새로 고치면 사라집니다.
          생성된 이미지는 이용자가 직접 내려받기 전까지 어디에도 보관되지 않습니다.</p>

        <h3>4. 제3자 서비스</h3>
        <p>본 사이트는 <b>외부 서버로 나가는 요청이 전혀 없습니다.</b> 도표와 코드 강조는 미리 만들어 페이지 안에 담았기 때문에,
          외부 CDN·폰트·스크립트를 불러오지 않습니다. 따라서 이용자의 접속 정보가 제3자에게 전달되지 않습니다.</p>
        <table>
          <tr><th>서비스</th><th>제공자</th><th>이용 목적</th></tr>
          <tr><td>Vercel</td><td>Vercel Inc.</td><td>웹사이트 호스팅 및 전송 (서버 접속 기록이 남을 수 있음)</td></tr>
        </table>
        <p>제작자는 위 사업자로부터 이용자 개인을 식별할 수 있는 정보를 제공받지 않습니다.</p>

        <h3>5. 이용자의 통제권</h3>
        <ul>
          <li><b>저장소 설정</b> 탭에서 항목별로 저장을 끄거나 켤 수 있으며, 끄는 즉시 해당 값이 삭제됩니다.</li>
          <li>왼쪽 목차의 <b>초기화</b> 버튼으로 진도와 퀴즈 기록을 한 번에 지울 수 있습니다.</li>
          <li>브라우저 설정에서 이 사이트의 데이터를 삭제하셔도 됩니다.</li>
        </ul>

        <h3>6. 만 14세 미만 아동</h3>
        <p>본 사이트는 개인정보를 수집하지 않으므로 아동으로부터 별도로 수집하는 정보도 없습니다.</p>

        <h3>7. 변경 고지</h3>
        <p>본 방침이 변경되는 경우 본 사이트에 게시하는 방법으로 공지합니다.</p>

        <div class="legal-meta">시행일: 2026년 7월 26일 · 문의: 페이지 하단의 텔레그램 채널 또는 오픈채팅</div>
      </div>

      <!-- 저장소 설정 -->
      <div class="legal-pane" data-pane="storage" hidden>
        <div class="legal-note"><b>이 사이트는 쿠키를 사용하지 않습니다.</b> 아래 항목은 모두 이용자의 브라우저에만 저장되며
          서버로 전송되지 않습니다. 끄면 저장된 값이 즉시 삭제되고, 이후로는 저장하지 않습니다.</div>

        <div class="sw-row">
          <div class="sw-txt"><b>화면 테마 기억</b><span>밝은 테마 / 어두운 테마 선택을 다음 방문까지 유지합니다. <code>cc-theme</code></span></div>
          <button class="sw" type="button" role="switch" data-pref="theme" aria-checked="true" aria-label="화면 테마 기억"></button>
        </div>
        <div class="sw-row">
          <div class="sw-txt"><b>학습 진도 기억</b><span>읽은 챕터를 기록해 완주율과 목차 체크 표시에 사용합니다. <code>cc_read</code></span></div>
          <button class="sw" type="button" role="switch" data-pref="progress" aria-checked="true" aria-label="학습 진도 기억"></button>
        </div>
        <div class="sw-row">
          <div class="sw-txt"><b>퀴즈 답안 기억</b><span>푼 문항과 정답 수를 기록합니다. 끄면 수료증의 퀴즈 점수도 표시되지 않습니다. <code>cc_quiz</code></span></div>
          <button class="sw" type="button" role="switch" data-pref="quiz" aria-checked="true" aria-label="퀴즈 답안 기억"></button>
        </div>
        <div class="sw-row">
          <div class="sw-txt"><b>설정값 저장</b><span>위 선택을 기억하기 위한 항목이라 끌 수 없습니다. <code>cc_prefs</code></span></div>
          <span class="sw-required">필수</span>
        </div>

        <div class="sw-state" id="swState"></div>
        <div class="legal-actions">
          <button type="button" id="swClearAll" class="danger">저장된 데이터 모두 삭제</button>
          <button type="button" data-tab="privacy">개인정보처리방침 보기</button>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- 최초 방문 안내 -->
<div class="consent" id="consent">
  <div class="consent-in">
    <p><b>이 사이트는 쿠키와 추적 도구를 사용하지 않습니다.</b><br>
      학습 진도와 화면 테마만 이용자의 브라우저에 저장되며, 서버로 전송되지 않습니다. 저장을 원하지 않으시면 설정에서 끄실 수 있습니다.</p>
    <div class="consent-btns">
      <button type="button" id="consentPrefs">저장소 설정</button>
      <button type="button" id="consentOk" class="primary">확인</button>
    </div>
  </div>
</div>
<div class="layout">
  <aside class="sidebar" id="sidebar">
    <div class="brand">
      <span class="dot"></span>
      <div><b>Claude Code 마스터 클래스</b><small>한국어 종합 실전 강의 · 17 chapters</small></div>
    </div>
    <button class="search-trigger" id="searchBtn"><span>🔍</span><span>검색</span><kbd>Ctrl K</kbd></button>
    <div class="read-progress" id="readProgress"></div>
    <nav aria-label="강의 목차">
      <a class="toc-ch" href="#top"><span class="toc-num">◆</span><span>개요</span></a>
      {{SIDEBAR}}
    </nav>
  </aside>
  <main class="main">
    <button class="icon-btn theme-toggle" id="themeBtn" aria-label="테마 전환">◐</button>
    <div class="content">
      <div id="top">
        <div class="hero">
          <div class="kicker">Master Class</div>
          <h1>Claude Code 마스터 클래스</h1>
          <p>설치부터 오케스트레이션까지 — Claude Code의 확장 기능 전반을 하나의 강의로 정리했습니다.</p>
          <p>각 챕터는 실제 설정 예제·표·흐름도로 개념을 단계적으로 익히도록 구성되어 있습니다.</p>
          <div class="toc-pills">
            <span>설치·시작</span><span>권한·플랜</span><span>모델</span><span>명령어</span><span>CLAUDE.md</span><span>자동 기억</span><span>서브에이전트</span><span>스킬</span><span>훅</span><span>MCP·플러그인</span><span>오케스트레이션</span><span>컨텍스트 엔지니어링</span><span>하네스·루프</span><span>프롬프트 가이드</span><span>플레이그라운드</span><span>부록</span><span>참고 자료</span>
          </div>
        </div>
      </div>
      {{CONTENT}}
      <footer class="site-footer">
        <div class="credit">제작 · <b>AI_Innovation_Studio</b></div>
        <div class="foot-links">
          <a href="https://t.me/aiinnovationstudio" target="_blank" rel="noopener noreferrer">✈️ AI 정보 텔레그램</a>
          <a href="https://open.kakao.com/o/s4OEqBai" target="_blank" rel="noopener noreferrer">💬 AI 정보공유 단톡방 참여문의</a>
        </div>
        <div class="foot-legal">
          <button type="button" data-legal="terms">이용약관</button>
          <button type="button" data-legal="privacy">개인정보처리방침</button>
          <button type="button" data-legal="storage">저장소 설정</button>
          <button type="button" id="printBtn" title="브라우저 인쇄 대화상자에서 PDF로 저장할 수 있습니다">🖨 인쇄 · PDF 저장</button>
        </div>
        <p class="disclaimer">본 강의는 공개된 공식 문서를 참고해 제작한 <b>비공식 학습 자료</b>이며, Anthropic PBC와 제휴·후원·승인 관계가 없습니다.
          Claude 및 Claude Code는 Anthropic PBC의 상표입니다. · 이 사이트는 쿠키와 추적 도구를 사용하지 않습니다.</p>
        <p class="disclaimer">© 2026 AI_Innovation_Studio. All rights reserved.</p>
      </footer>
    </div>
  </main>
</div>

<script type="module">
// tools/prerender.mjs 를 거쳤다면 도표는 이미 인라인 SVG라 mermaid를 받을 필요가 없다.
// 아직 <pre class="mermaid"> 가 남아 있을 때만(= 후처리를 건너뛴 빌드) CDN에서 불러온다.
if(document.querySelector('pre.mermaid')){
  const mermaid = (await import('https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs')).default;
  const MERMAID_FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", sans-serif';
  const themeVars = () => document.documentElement.getAttribute('data-theme') !== 'light' ? 'dark' : 'default';
  const renderMermaid = () => {
    mermaid.initialize({startOnLoad:false, theme:themeVars(), securityLevel:'loose',
      fontFamily: MERMAID_FONT,
      flowchart:{ htmlLabels:true, useMaxWidth:true, padding:14 },
      themeVariables:{ fontFamily: MERMAID_FONT, fontSize:'15px' }});
    document.querySelectorAll('pre.mermaid').forEach(el=>{
      if(!el.dataset.src) el.dataset.src = el.textContent;
      el.removeAttribute('data-processed');
      el.innerHTML = el.dataset.src;
    });
    mermaid.run({querySelector:'pre.mermaid'});
  };
  window.__renderMermaid = renderMermaid;
  renderMermaid();
}
</script>
<script src="https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js" integrity="sha384-F/bZzf7p3Joyp5psL90p/p89AZJsndkSoGwRpXcZhleCWhd8SnRuoYo4d0yirjJp" crossorigin="anonymous"></script>
<script>
document.querySelectorAll('pre code').forEach(b=>{
  if(!b.className.includes('mermaid')) window.hljs && hljs.highlightElement(b);
});

// ===== 저장소 설정 =====
// 이 사이트는 쿠키를 사용하지 않는다. 아래 항목만 브라우저 localStorage에 저장하며,
// 이용자가 [저장소 설정]에서 끄면 즉시 삭제하고 이후 저장하지 않는다.
const PREF_KEY='cc_prefs';
const STORE_KEYS={theme:'cc-theme',progress:'cc_read',quiz:'cc_quiz'};
const prefs=(function(){
  const d={theme:true,progress:true,quiz:true,ack:false};
  try{ const v=localStorage.getItem(PREF_KEY); if(v) Object.assign(d,JSON.parse(v)); }catch(_){}
  return d;
})();
function savePrefs(){ try{localStorage.setItem(PREF_KEY,JSON.stringify(prefs));}catch(_){} }

// theme toggle
const root=document.documentElement;
const hljsTheme=document.getElementById('hljs-theme');
const LIGHT_HL='https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github.min.css';
const DARK_HL='https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github-dark.min.css';
function applyTheme(t){
  root.setAttribute('data-theme',t);
  if(hljsTheme) hljsTheme.href = t==='light'?LIGHT_HL:DARK_HL;   // 후처리로 인라인되면 null
  if(prefs.theme){ try{localStorage.setItem('cc-theme',t)}catch(e){} }
  if(window.__renderMermaid) window.__renderMermaid();
}
document.querySelectorAll('#themeBtn,#themeBtnM').forEach(btn=>btn.addEventListener('click',()=>{
  applyTheme(root.getAttribute('data-theme')==='light'?'dark':'light');
}));
// 수동 토글 전이면 OS 테마 변경을 실시간으로 따라감
if(window.matchMedia){
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change',e=>{
    let saved=null; try{saved=localStorage.getItem('cc-theme')}catch(_){}
    if(!saved) applyTheme(e.matches?'dark':'light');
  });
}

// mobile nav
const menuBtn=document.getElementById('menuBtn'), backdrop=document.getElementById('backdrop');
function closeNav(){document.body.classList.remove('nav-open')}
menuBtn&&menuBtn.addEventListener('click',()=>document.body.classList.toggle('nav-open'));
backdrop&&backdrop.addEventListener('click',closeNav);

// scroll-spy + progress
const chapters=[...document.querySelectorAll('.chapter, #top')];
const chLinks=new Map();
document.querySelectorAll('.toc-ch').forEach(a=>{
  const id=a.getAttribute('href').slice(1); chLinks.set(id,a);
});
const progress=document.getElementById('progress');
let suppressSpy=false, spyTimer=0;

function setActiveChapter(chId){   // 현재 위치 강조만 (펼침 상태는 사용자가 직접 제어)
  chLinks.forEach((a,cid)=>a.classList.toggle('active',cid===chId));
}
function onScroll(){
  const st=window.scrollY, dh=document.body.scrollHeight-window.innerHeight;
  progress.style.width=(dh>0?(st/dh*100):0)+'%';
  if(suppressSpy) return;               // 클릭 이동 중엔 사이드바 플리커 방지
  let cur=chapters[0];
  for(const s of chapters){ if(s.getBoundingClientRect().top<=120) cur=s; }
  setActiveChapter(cur.id);
  // 소제목은 "현재 챕터" 안에서만 찾는다. 문서 전체의 h2 위치를 읽으면 건너뛴
  // 챕터까지 강제로 레이아웃돼 content-visibility 이득이 통째로 사라진다.
  // (.chapter 자기 자신의 rect 는 추정 높이로 답하므로 위 루프는 저렴하다)
  const subs=cur.classList.contains('chapter')?[...cur.querySelectorAll('.content h2[id]')]:[];
  let curSub=null;
  for(const h of subs){ if(h.getBoundingClientRect().top<=140) curSub=h.id; }
  document.querySelectorAll('.toc-sub').forEach(a=>{
    a.classList.toggle('active', a.getAttribute('href')==='#'+curSub);
  });
}
document.addEventListener('scroll',onScroll,{passive:true});
window.addEventListener('resize',onScroll);
onScroll();

// 부드러운 앵커 이동 (사이드바·본문·검색 공통)
function navTo(href,elOverride){
  // elOverride: 본문 검색 히트처럼 id가 없는 요소로 직접 이동할 때 사용(주소·목차는 href 기준 유지)
  const t=elOverride||document.getElementById(decodeURIComponent(href.slice(1)));
  if(!t) return false;
  closeNav();
  const chEl=t.closest('.chapter');
  setActiveChapter(chEl?chEl.id:'top');
  document.querySelectorAll('.toc-sub').forEach(x=>x.classList.toggle('active',x.getAttribute('href')===href));
  suppressSpy=true;
  t.scrollIntoView({behavior:'smooth',block:elOverride?'center':'start'});
  try{history.replaceState(null,'',href);}catch(_){}
  clearTimeout(spyTimer);
  spyTimer=setTimeout(()=>{suppressSpy=false;onScroll();},650);
  return true;
}
document.querySelectorAll('a[href^="#"]').forEach(a=>{
  a.addEventListener('click',e=>{
    const href=a.getAttribute('href'); if(href.length<=1) return;
    if(a.classList.contains('toc-ch')){
      const g=a.closest('.toc-group');
      if(g && g.classList.contains('has-subs')) g.classList.toggle('open');   // 독립 토글(다중 펼침) — 다른 챕터는 그대로
    }
    if(navTo(href)) e.preventDefault();
  });
});

// 외부 링크는 새 탭에서
document.querySelectorAll('.content a[href^="http"]').forEach(a=>{a.target='_blank';a.rel='noopener noreferrer';});

// ===== localStorage 헬퍼 =====
const LS=(k,d)=>{try{const v=localStorage.getItem(k);return v==null?d:JSON.parse(v);}catch(_){return d;}};
const GATE={cc_read:'progress',cc_quiz:'quiz'};   // 설정에서 끈 항목은 저장하지 않는다
const LSset=(k,v)=>{const g=GATE[k]; if(g&&!prefs[g]) return; try{localStorage.setItem(k,JSON.stringify(v));}catch(_){}};

// ===== 코드 복사 버튼 =====
document.querySelectorAll('.content pre:not(.mermaid)').forEach(pre=>{
  const code=pre.querySelector('code'); if(!code) return;
  const btn=document.createElement('button'); btn.className='copy-btn'; btn.type='button'; btn.textContent='복사';
  btn.addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(code.innerText);}
    catch(_){const r=document.createRange();r.selectNode(code);const s=getSelection();s.removeAllRanges();s.addRange(r);try{document.execCommand('copy');}catch(__){}s.removeAllRanges();}
    btn.textContent='✓ 복사됨'; btn.classList.add('done');
    setTimeout(()=>{btn.textContent='복사';btn.classList.remove('done');},1400);
  });
  pre.appendChild(btn);
});

// 진도·퀴즈 상태는 서로를 참조하므로(초기화 버튼) 선언을 먼저 모아 둔다
const quizState=LS('cc_quiz',{});
const quizChip=document.getElementById('quizStat');

// ===== 읽은 챕터 진도 =====
const readSet=new Set(LS('cc_read',[]));
const rpEl=document.getElementById('readProgress');
const totalCh=chapters.filter(c=>c.classList.contains('chapter')).length;
function renderProgress(){
  chLinks.forEach((a,cid)=>{ if(cid!=='top') a.classList.toggle('done',readSet.has(cid)); });
  const n=readSet.size, pct=Math.round(n/totalCh*100);
  rpEl.innerHTML='<div class="rp-top"><span>📖 완주 '+n+'/'+totalCh+' <b style="color:var(--accent2)">'+pct+'%</b></span>'
    +(n||Object.keys(quizState).length?'<button class="rp-reset" type="button" id="rpReset" title="읽은 챕터·퀴즈 기록을 지웁니다">초기화</button>':'')
    +'</div><div class="rbar"><i style="width:'+pct+'%"></i></div>';
  document.getElementById('rpReset')?.addEventListener('click',resetProgress);
}
function resetProgress(){
  if(!confirm('읽은 챕터 진도와 퀴즈 답안을 모두 지웁니다. 계속할까요?')) return;
  readSet.clear(); LSset('cc_read',[]);
  for(const k in quizState) delete quizState[k];
  LSset('cc_quiz',{});
  document.querySelectorAll('.quiz-q').forEach(clearQuizQ);
  document.querySelectorAll('.quiz-retry').forEach(b=>b.hidden=true);
  renderQuizChip(); renderProgress();
  restartTop();
}
// 지운 직후 하단에 머물러 있으면 스크롤 이벤트가 곧바로 진도를 다시 기록한다.
// '처음부터 다시'가 되도록 맨 위로 되돌린다.
function restartTop(){
  // behavior:'auto'는 CSS의 scroll-behavior:smooth를 따르므로 천천히 올라가고,
  // 그 사이 지나친 챕터가 다시 기록된다. 'instant'로 즉시 이동해야 한다.
  window.scrollTo({top:0,behavior:'instant'});
  setActiveChapter('top');
}
function markProgress(){
  let changed=false;
  const atBottom = window.innerHeight+window.scrollY >= document.body.scrollHeight-80;
  chapters.forEach(s=>{
    if(s.id==='top' || readSet.has(s.id)) return;
    if(s.getBoundingClientRect().bottom<window.innerHeight*0.55 || atBottom){ readSet.add(s.id); changed=true; }
  });
  if(changed){ LSset('cc_read',[...readSet]); renderProgress(); }
}
renderProgress();
window.addEventListener('scroll',markProgress,{passive:true});
markProgress();

// ===== 퀴즈 점수 =====
function quizStats(){
  const all=[...document.querySelectorAll('.quiz-q')]; let answered=0,correct=0;
  all.forEach(q=>{ const id=q.dataset.qid; if(id in quizState){ answered++; if(quizState[id]===parseInt(q.dataset.answer,10)) correct++; } });
  return {total:all.length,answered,correct};
}
function renderQuizChip(){
  const s=quizStats();
  if(!s.answered){ quizChip.style.display='none'; return; }
  quizChip.style.display='inline-flex';
  quizChip.innerHTML='🧩 퀴즈 '+s.answered+'/'+s.total+' · 정답 <b style="color:#3aa76d;margin-left:4px">'+s.correct+'</b>';
}
function applyAnswer(q,chosen){
  const ans=parseInt(q.dataset.answer,10); const opts=[...q.querySelectorAll('.quiz-opt')];
  q.classList.add('answered');
  if(opts[ans]) opts[ans].classList.add('correct');
  if(chosen!==ans && opts[chosen]) opts[chosen].classList.add('wrong');
}
function clearQuizQ(q){
  q.classList.remove('answered');
  q.querySelectorAll('.quiz-opt').forEach(o=>o.classList.remove('correct','wrong'));
}
// 한 챕터의 퀴즈 안에 답한 문항이 하나라도 있으면 '다시 풀기' 노출
function syncRetry(quizEl){
  const btn=quizEl.querySelector('.quiz-retry'); if(!btn) return;
  btn.hidden = ![...quizEl.querySelectorAll('.quiz-q')].some(q=>q.dataset.qid in quizState);
}
document.querySelectorAll('.quiz-q').forEach(q=>{
  const id=q.dataset.qid; const opts=[...q.querySelectorAll('.quiz-opt')];
  if(id in quizState) applyAnswer(q,quizState[id]);
  opts.forEach((o,i)=>o.addEventListener('click',()=>{
    if(q.classList.contains('answered')) return;
    quizState[id]=i; LSset('cc_quiz',quizState);
    applyAnswer(q,i); renderQuizChip(); renderProgress(); syncRetry(q.closest('.quiz')); setTimeout(onScroll,50);
  }));
});
document.querySelectorAll('.quiz').forEach(quizEl=>{
  syncRetry(quizEl);
  quizEl.querySelector('.quiz-retry')?.addEventListener('click',()=>{
    quizEl.querySelectorAll('.quiz-q').forEach(q=>{ delete quizState[q.dataset.qid]; clearQuizQ(q); });
    LSset('cc_quiz',quizState);
    renderQuizChip(); renderProgress(); syncRetry(quizEl);
    quizEl.scrollIntoView({behavior:'smooth',block:'nearest'});
  });
});
renderQuizChip();
quizChip.addEventListener('click',()=>{ document.querySelector('.cert-app')?.scrollIntoView({behavior:'smooth',block:'center'}); });

// ===== 통합 검색 (Ctrl/Cmd+K) =====
const esc=s=>s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const norm=s=>s.replace(/\s+/g,' ').trim();

// 인덱스: 챕터(kind ch) → 소제목(kind h) → 본문 블록(kind b)
// 본문 블록은 DOM 참조를 들고 있다가, 클릭 시 그 자리로 이동+강조한다.
// 전체 본문을 훑는 작업이라 파싱 시점에 하면 첫 화면이 그만큼 늦어진다.
// 검색은 사용자가 열기 전엔 쓰이지 않으므로 첫 열람 때 한 번만 만든다.
const sIdx=[];
let sIdxReady=false;
function buildSearchIndex(){
  if(sIdxReady) return;
  sIdxReady=true;
  document.querySelectorAll('.chapter').forEach(ch=>{
    const chTitle=norm(ch.querySelector('.ch-title')?.textContent||'');
    const chNum=norm(ch.querySelector('.ch-badge')?.textContent||'').replace('CHAPTER ','');
    sIdx.push({kind:'ch',href:'#'+ch.id,title:chTitle,num:chNum,sub:''});

    let anchor='#'+ch.id, section='';
    const nodes=ch.querySelectorAll('h2[id],h3[id],p,li,td,th,blockquote,pre>code,.quiz-question,.quiz-explain');
    nodes.forEach(el=>{
      if(/^H[23]$/.test(el.tagName)){
        section=norm(el.textContent); anchor='#'+el.id;
        sIdx.push({kind:'h',href:anchor,title:section,num:'',sub:chTitle});
        return;
      }
      // 중첩 블록(li 안의 p 등)은 가장 안쪽만 인덱싱해 중복을 막는다
      if(el.querySelector('p,li,td,th,blockquote,pre>code')) return;
      const text=norm(el.textContent);
      if(text.length<2) return;
      sIdx.push({kind:'b',href:anchor,title:section||chTitle,num:'',sub:chTitle,body:text,el:el});
    });
  });
}
// 브라우저가 한가해지면 미리 만들어 둔다 — 첫 Ctrl+K 가 즉시 열리도록.
// requestIdleCallback 이 없으면(Safari 구버전) 열 때 만들어도 충분히 빠르다.
if(window.requestIdleCallback) requestIdleCallback(buildSearchIndex,{timeout:4000});
const sModal=document.getElementById('searchModal'), sInput=document.getElementById('searchInput'), sRes=document.getElementById('searchResults');
let sSel=0, sList=[];
// 매치 주변만 잘라 <mark>로 강조한 스니펫
function snippet(text,q,pos){
  const pad=52;
  let s=Math.max(0,pos-pad), e=Math.min(text.length,pos+q.length+pad);
  return (s>0?'…':'')+esc(text.slice(s,pos))
    +'<mark>'+esc(text.slice(pos,pos+q.length))+'</mark>'
    +esc(text.slice(pos+q.length,e))+(e<text.length?'…':'');
}
function renderSearch(){
  const q=sInput.value.trim().toLowerCase();
  sSel=0;
  if(!q){
    sList=sIdx.filter(it=>it.kind!=='b').slice(0,40);
    paintSearch(q,sIdx.filter(it=>it.kind!=='b').length);
    return;
  }
  const hits=[];
  for(const it of sIdx){
    const tPos=it.title.toLowerCase().indexOf(q);
    if(it.kind!=='b' && tPos>=0){ hits.push({it,score:it.kind==='ch'?0:1,tPos,bPos:-1}); continue; }
    if(it.kind==='b'){
      const bPos=it.body.toLowerCase().indexOf(q);
      if(bPos>=0) hits.push({it,score:2,tPos:-1,bPos});
    }
  }
  hits.sort((a,b)=>a.score-b.score);          // 문서 순서는 안정 정렬로 유지
  sList=hits.slice(0,40);
  paintSearch(q,hits.length);
}
function paintSearch(q,total){
  if(!sList.length){ sRes.innerHTML='<div class="search-empty">결과 없음</div>'; return; }
  const rows=sList.map((h,i)=>{
    const it=h.it||h, sel=i===0?'sel':'';
    const title=esc(it.title), sub=it.sub?'<span class="r-sub">'+esc(it.sub)+'</span>':'';
    const snip=(h.bPos>=0)?'<span class="r-snip">'+snippet(it.body,q,h.bPos)+'</span>':'';
    return '<a href="'+it.href+'" class="'+sel+'"><span class="r-num">'+esc(it.num||(it.kind==='b'?'¶':'§'))
      +'</span><span><span class="r-title">'+title+sub+'</span>'+snip+'</span></a>';
  }).join('');
  const head=(total>sList.length)?'<div class="search-count">'+total+'건 중 '+sList.length+'건 표시</div>':'';
  sRes.innerHTML=head+rows;
  [...sRes.querySelectorAll('a')].forEach((el,i)=>{ el.addEventListener('click',e=>{e.preventDefault();pick(i);}); el.addEventListener('mousemove',()=>setSel(i)); });
}
function setSel(i){ sSel=i; [...sRes.querySelectorAll('a')].forEach((a,j)=>a.classList.toggle('sel',j===i)); }
function pick(i){
  const h=sList[i]; if(!h) return;
  const it=h.it||h;
  searchPrevFocus=null;                       // 결과로 이동할 땐 검색 버튼으로 포커스를 되돌리지 않는다
  closeSearch();
  navTo(it.href,it.el);                       // 본문 히트면 그 블록으로 직접 이동
  if(it.el) flashWhenSettled(it.el);
}
// 부드러운 스크롤은 거리에 따라 2초 넘게 걸린다 — 멈춘 뒤에 강조해야 눈에 보인다
function flashWhenSettled(el){
  let last=-1, still=0; const t0=performance.now();
  (function tick(){
    const y=window.scrollY;
    if(y===last){ if(++still>=3) return flash(el); } else { still=0; last=y; }
    if(performance.now()-t0>3000) return flash(el);
    requestAnimationFrame(tick);
  })();
}
function flash(el){
  el.classList.remove('hit-flash');
  void el.offsetWidth;                        // 애니메이션 재시작
  el.classList.add('hit-flash');
  setTimeout(()=>el.classList.remove('hit-flash'),1700);
}
let searchPrevFocus=null;
function openSearch(){
  // 법적 고지 모달이 떠 있으면 겹쳐 열지 않고 그쪽을 먼저 닫는다
  if(legalModal.classList.contains('open')) closeLegal();
  searchPrevFocus=document.activeElement;
  buildSearchIndex();                         // 유휴 시간에 못 만들었으면 여기서 만든다
  sModal.classList.add('open'); sInput.value=''; renderSearch(); setTimeout(()=>sInput.focus(),0);
}
function closeSearch(){
  sModal.classList.remove('open');
  if(searchPrevFocus&&searchPrevFocus.focus) searchPrevFocus.focus({preventScroll:true});
  searchPrevFocus=null;
}
sInput.addEventListener('input',renderSearch);
sInput.addEventListener('keydown',e=>{
  if(e.key==='ArrowDown'){e.preventDefault();setSel(Math.min(sSel+1,sList.length-1));sRes.querySelector('a.sel')?.scrollIntoView({block:'nearest'});}
  else if(e.key==='ArrowUp'){e.preventDefault();setSel(Math.max(sSel-1,0));sRes.querySelector('a.sel')?.scrollIntoView({block:'nearest'});}
  else if(e.key==='Enter'){e.preventDefault();pick(sSel);}
});
sModal.addEventListener('click',e=>{ if(e.target===sModal) closeSearch(); });
document.getElementById('searchBtn')?.addEventListener('click',openSearch);
document.getElementById('searchBtnM')?.addEventListener('click',openSearch);
document.addEventListener('keydown',e=>{ if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openSearch();} });
// Esc 는 문서 전체에서 받는다 — 결과 목록으로 Tab 이동한 뒤에도 닫혀야 하므로
// 입력창 keydown 에 걸어 두면 안 된다
document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&sModal.classList.contains('open')){e.preventDefault();closeSearch();} });

// ===== 수료증 =====
const certApp=document.querySelector('.cert-app');
if(certApp){
  certApp.innerHTML='<div class="cert-form"><input id="certName" type="text" placeholder="이름을 입력하세요" maxlength="24" spellcheck="false"><button class="cert-btn" id="certGen" type="button">수료증 생성</button><button class="cert-btn ghost" id="certDl" type="button">PNG 저장</button></div><div class="cert-stat" id="certStat"></div><canvas id="certCanvas" width="1200" height="820"></canvas><div class="cert-note" id="certNote"><b>💾 저장 방법</b><br>• <b>PC:</b> <b>PNG 저장</b> 버튼을 누르면 브라우저 <b>다운로드 폴더</b>에 이미지로 저장됩니다. (수료증을 마우스 <b>우클릭 → 이미지를 다른 이름으로 저장</b>도 됩니다.)<br>• <b>모바일:</b> 수료증 이미지를 <b>길게 눌러 「이미지 저장」</b>을 선택하세요. (기기·브라우저에 따라 <b>PNG 저장</b> 버튼도 동작합니다.)</div>';
  const cName=document.getElementById('certName'), cGen=document.getElementById('certGen'), cDl=document.getElementById('certDl'), cCanvas=document.getElementById('certCanvas'), cStat=document.getElementById('certStat'), cNote=document.getElementById('certNote');
  function roundRect(x,y,w,h,r){const c=cCanvas.getContext('2d');c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath();}
  function updStat(){ const s=quizStats(); const pct=s.answered?Math.round(s.correct/s.answered*100):0; cStat.innerHTML='읽은 챕터 <b>'+readSet.size+'/'+totalCh+'</b> · 퀴즈 정답 <b>'+s.correct+'/'+s.answered+'</b>'+(s.answered?' ('+pct+'%)':''); }
  function draw(){
    const name=cName.value.trim()||'수료자'; const s=quizStats(); const W=1200,H=820; const c=cCanvas.getContext('2d');
    const g=c.createLinearGradient(0,0,W,H); g.addColorStop(0,'#17130f'); g.addColorStop(.55,'#0e0f13'); g.addColorStop(1,'#0b0c10'); c.fillStyle=g; c.fillRect(0,0,W,H);
    const rg=c.createRadialGradient(W*0.8,H*0.15,0,W*0.8,H*0.15,720); rg.addColorStop(0,'rgba(224,122,75,.20)'); rg.addColorStop(1,'rgba(224,122,75,0)'); c.fillStyle=rg; c.fillRect(0,0,W,H);
    c.strokeStyle='#2a2d38'; c.lineWidth=2; roundRect(40,40,W-80,H-80,18); c.stroke();
    c.strokeStyle='#e07a4b'; c.lineWidth=4; c.beginPath(); c.moveTo(58,54); c.lineTo(W-58,54); c.stroke();
    c.lineCap='round'; c.lineJoin='round'; c.strokeStyle='#e07a4b'; c.lineWidth=8;
    c.beginPath(); c.moveTo(W/2-24,92); c.lineTo(W/2-4,110); c.lineTo(W/2-24,128); c.stroke();
    c.fillStyle='#c9a86a'; roundRect(W/2,120,26,8,4); c.fill();
    c.textAlign='center';
    c.fillStyle='#c9a86a'; c.font='600 22px monospace'; c.fillText('C E R T I F I C A T E   O F   C O M P L E T I O N',W/2,190);
    c.fillStyle='#e7e3da'; c.font='800 56px sans-serif'; c.fillText('Claude Code 마스터 클래스',W/2,270);
    c.fillStyle='#a7a396'; c.font='400 25px sans-serif'; c.fillText('아래 수료자가 본 강의 과정을 이수하였음을 증명합니다',W/2,340);
    c.fillStyle='#e07a4b'; c.font='800 74px sans-serif'; c.fillText(name,W/2,455);
    c.strokeStyle='#2a2d38'; c.lineWidth=1; c.beginPath(); c.moveTo(W/2-270,485); c.lineTo(W/2+270,485); c.stroke();
    const pct=s.answered?Math.round(s.correct/s.answered*100):0;
    c.fillStyle='#cbc7ba'; c.font='600 28px sans-serif'; c.fillText(totalCh+'개 챕터 · 퀴즈 정답 '+s.correct+'/'+s.answered+(s.answered?' ('+pct+'%)':''),W/2,560);
    const d=new Date(); const ds=d.getFullYear()+'.'+String(d.getMonth()+1).padStart(2,'0')+'.'+String(d.getDate()).padStart(2,'0');
    c.fillStyle='#7f7c72'; c.font='400 22px monospace'; c.fillText(ds,W/2,660);
    c.fillStyle='#c9a86a'; c.font='700 24px monospace'; c.fillText('제작 · AI_Innovation_Studio',W/2,712);
    c.fillStyle='#7f7c72'; c.font='400 19px monospace'; c.fillText('claude-code-tutorial-ko.vercel.app',W/2,748);
    cCanvas.style.display='block'; cDl.style.display='inline-block'; cNote.style.display='block';
  }
  updStat();
  cGen.addEventListener('click',()=>{updStat();draw();});
  cName.addEventListener('keydown',e=>{ if(e.key==='Enter'){updStat();draw();} });
  cDl.addEventListener('click',()=>{ cCanvas.toBlob(bl=>{ const u=URL.createObjectURL(bl); const a=document.createElement('a'); a.href=u; a.download='claude-code-마스터클래스-수료증.png'; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(u),1000); }); });
}

// ===== 플레이그라운드 · 터미널 놀이터 =====
const pgt=document.querySelector('.pg-terminal');
if(pgt){
  pgt.innerHTML='<div class="pg-bar"><i></i><i></i><i></i><span>claude — 놀이터</span></div><div class="pg-out" id="pgOut"></div><div class="pg-inline"><span class="p">❯</span><input id="pgIn" type="text" placeholder="/help 를 입력해 보세요" autocomplete="off" spellcheck="false"></div>';
  const out=pgt.querySelector('#pgOut'), inp=pgt.querySelector('#pgIn');
  const CMDS={
    '/help':()=>['<span class="k">사용 가능한 명령</span>','/clear · /compact · /context — 컨텍스트 관리','/model · /effort · /fast — 모델·성능','/init · /memory · /agents · /mcp · /hooks — 설정','/status · /usage · /doctor · /rewind — 진단·되돌리기','아무 문장이나 입력 → Claude가 작업 시작(시뮬레이션)'],
    '/clear':()=>{out.innerHTML='';return['<span class="ok">✓ 컨텍스트를 리셋했습니다.</span> 새 대화를 시작합니다.'];},
    '/context':()=>['<span class="k">컨텍스트</span> 42,300 / 1,000,000 토큰 (4%) 사용','여유롭습니다. 길어지면 /compact 로 압축하세요.'],
    '/compact':()=>['<span class="ok">✓ 대화를 요약해 컨텍스트를 확보했습니다.</span> 핵심 결정·미해결 이슈는 보존됩니다.'],
    '/init':()=>['<span class="ok">✓ CLAUDE.md 생성됨.</span> 빌드 명령·테스트·규칙을 감지해 시작 파일을 만들었습니다.'],
    '/agents':()=>['<span class="k">서브에이전트</span> Explore · Plan · general-purpose(내장)','.claude/agents/ 에 커스텀 정의를 추가할 수 있습니다.'],
    '/mcp':()=>['<span class="k">MCP 서버</span> 연결된 서버 없음. `claude mcp add` 로 외부 도구를 연결하세요.'],
    '/hooks':()=>['<span class="k">훅</span> 구성된 훅 없음. .claude/settings.json 의 hooks 블록에 정의합니다.'],
    '/status':()=>['<span class="k">세션</span> 모델 claude-opus-5 · effort high · 정상'],
    '/usage':()=>['<span class="k">사용량</span> 오늘 입력 128K · 출력 34K · 예상 $1.49'],
    '/fast':()=>['<span class="ok">✓ 빠른 모드 ON</span> — 최근 Opus를 최대 2.5배 빠르게(프리미엄).'],
    '/rewind':()=>['<span class="k">되감기</span> 체크포인트 3개. Esc 를 두 번 눌러도 열립니다.'],
    '/memory':()=>['<span class="k">기억</span> MEMORY.md 색인 로드됨(앞 200줄). 자동 기억 ON.'],
    '/permissions':()=>['<span class="k">권한</span> 기본(default) 모드. Shift+Tab 으로 순환합니다.'],
    '/doctor':()=>['<span class="ok">✓ 설치 정상</span> 버전 2.1.x · ripgrep OK · 설정 유효.'],
  };
  function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
  function print(lines,cls){ lines.forEach(l=>{const d=document.createElement('div'); if(cls)d.className=cls; d.innerHTML=l; out.appendChild(d);}); out.scrollTop=out.scrollHeight; }
  function run(cmd){
    cmd=cmd.trim(); if(!cmd) return;
    print(['❯ '+esc(cmd)],'u');
    const parts=cmd.split(/\s+/), base=parts[0], arg=(parts[1]||'').trim();
    if(base==='/model'){ print(arg?['<span class="ok">✓ 모델을 '+esc(arg)+' 로 설정</span>했습니다.']:['<span class="k">모델</span> opus · sonnet · haiku · fable 중 선택. 예: /model opus'],'sys'); }
    else if(base==='/effort'){ const ok=['low','medium','high','xhigh','max'].includes(arg); print(arg?(ok?['<span class="ok">✓ effort '+arg+' 적용.</span> 어려운 코딩·에이전틱 작업엔 xhigh 권장.']:['<span class="err">알 수 없는 effort:</span> low·medium·high·xhigh·max 중에서 고르세요.']):['<span class="k">effort</span> 기본 high. 예: /effort xhigh'],'sys'); }
    else if(base[0]==='/'){ const fn=CMDS[base]; if(fn) print(fn(),'sys'); else print(['<span class="err">명령을 찾을 수 없습니다:</span> '+esc(base)+' — <span class="k">/help</span> 를 입력해 보세요.']); }
    else { print(['<span class="sys">Claude가 작업을 시작합니다… (시뮬레이션)</span>','<span class="sys">탐색 → 계획 → 구현 → 검증. 실제 Claude Code는 여기서 파일을 읽고 코드를 수정합니다.</span>']); }
  }
  inp.addEventListener('keydown',e=>{ if(e.key==='Enter'){ run(inp.value); inp.value=''; } });
  print(['<span class="sys">Claude Code 놀이터입니다. <span class="k">/help</span> 로 시작하세요. (학습용 시뮬레이터)</span>']);
  const chips=document.createElement('div'); chips.className='pg-chips';
  ['/help','/model opus','/effort xhigh','/context','/clear'].forEach(c=>{const b=document.createElement('button');b.type='button';b.textContent=c;b.addEventListener('click',()=>{run(c);inp.focus();});chips.appendChild(b);});
  pgt.after(chips);
}

// ===== 플레이그라운드 · 확장 진단 위저드 =====
const pgw=document.querySelector('.pg-wizard');
if(pgw){
  const RES={
    claudemd:{t:'CLAUDE.md',d:'매번 다시 설명하게 되는 <strong>사실·규칙</strong>이라면 프로젝트 지침 파일에 담으세요. 짧고 구체적으로(200줄 이하) 유지하는 게 핵심입니다.',href:'#ch5'},
    skill:{t:'스킬(Skill)',d:'가끔 필요한 <strong>다단계 절차·도메인 지식</strong>이라면 온디맨드로 로드되는 스킬로. 이제 명령어도 스킬로 통합됩니다.',href:'#ch8'},
    hook:{t:'훅(Hook)',d:'포맷·차단처럼 <strong>무조건 매번 실행</strong>돼야 하면 결정론적인 훅으로. CLAUDE.md의 "조언"과 달리 강제됩니다.',href:'#ch9'},
    subagent:{t:'서브에이전트',d:'탐색·테스트의 <strong>고출력을 격리</strong>하려면 독립 컨텍스트를 가진 서브에이전트로. 요약만 메인 대화로 돌아옵니다.',href:'#ch7'},
    mcp:{t:'MCP',d:'다른 도구의 데이터를 <strong>반복해서 복붙</strong>하고 있다면 MCP로 직접 연결하세요. 이슈트래커·DB·디자인 도구 등.',href:'#ch10'},
    memory:{t:'자동 기억',d:'Claude가 여러분의 교정에서 <strong>스스로 배우게</strong> 하고 싶다면 자동 기억이 발견·교정을 축적합니다.',href:'#ch6'},
  };
  const Q1={q:'지금 상황에 가장 가까운 것은?',opts:[
    ['같은 지시를 매번 반복해서 입력한다','ask2'],
    ['특정 작업을 한 번에 실행할 바로가기가 필요하다','skill'],
    ['어떤 동작이 무조건 매번 일어나야 한다(포맷·차단 등)','hook'],
    ['탐색·테스트 출력이 많아 메인 대화가 지저분해진다','subagent'],
    ['다른 도구(이슈·DB·디자인)의 데이터를 자꾸 복붙한다','mcp'],
    ['Claude가 내 교정에서 스스로 배우면 좋겠다','memory'],
  ]};
  const Q2={q:'그 반복되는 내용은 어느 쪽에 가깝나요?',opts:[
    ['항상 지켜야 할 사실·규칙(빌드 명령·코드 스타일 등)','claudemd'],
    ['여러 단계로 이뤄진 절차(배포·이슈 수정 루틴 등)','skill'],
  ]};
  function renderQ(Q){
    pgw.innerHTML='<div class="pg-q">'+Q.q+'</div><div class="pg-opts"></div>';
    const box=pgw.querySelector('.pg-opts');
    Q.opts.forEach(([label,next])=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.addEventListener('click',()=>{ next==='ask2'?renderQ(Q2):showRes(next); });box.appendChild(b);});
  }
  function showRes(key){
    const r=RES[key];
    pgw.innerHTML='<div class="pg-result"><span class="tag">추천</span><h4>'+r.t+'</h4><p>'+r.d+'</p><a href="'+r.href+'">해당 챕터로 →</a><div><button class="pg-again" type="button">다시 진단하기</button></div></div>';
    pgw.querySelector('.pg-again').addEventListener('click',()=>renderQ(Q1));
    const link=pgw.querySelector('.pg-result a'); link.addEventListener('click',e=>{e.preventDefault(); navTo(link.getAttribute('href'));});
  }
  renderQ(Q1);
}

// ===== 플레이그라운드 · 비용 계산기 =====
const pgc=document.querySelector('.pg-cost');
if(pgc){
  const KRW=1380; // 대략 환율(달러당)
  const M={ // [입력$, 출력$, 이름, 한줄 설명]
    'claude-haiku-4-5':[1,5,'Haiku 4.5','가볍고 빠름 · 가장 저렴'],
    'claude-sonnet-5':[3,15,'Sonnet 5','균형 잡힌 실무용'],
    'claude-opus-5':[5,25,'Opus 5','가장 똑똑 · 코딩 최강'],
    'claude-fable-5':[10,50,'Fable 5','최고 성능 · 가장 비쌈'],
  };
  const P={ // 시나리오 프리셋: [입력토큰, 출력토큰, 하루 횟수]
    '💬 가벼운 질문':[500,300,20], '🔧 코드 리뷰':[4000,1200,15], '📄 긴 문서 작업':[20000,4000,8],
  };
  pgc.innerHTML=
    '<div class="presets" id="ccPre"></div>'+
    '<div class="fld"><div class="lab"><b>① 어떤 모델을 쓸까요?</b></div><select id="ccModel"></select></div>'+
    '<div class="fld"><div class="lab"><b>② 하루에 몇 번 쓸까요?</b><span class="val" id="ccReqV"></span></div><input id="ccReq" type="range" min="1" max="200" value="20"></div>'+
    '<div class="fld"><div class="lab"><b>③ 내가 보내는 양 (입력)</b><span class="val" id="ccInV"></span></div><input id="ccIn" type="range" min="200" max="40000" step="200" value="4000"></div>'+
    '<div class="fld"><div class="lab"><b>④ Claude 답변 양 (출력)</b><span class="val" id="ccOutV"></span></div><input id="ccOut" type="range" min="100" max="12000" step="100" value="1000"></div>'+
    '<div class="out"><div class="krw" id="ccKrw">₩0</div><div class="usd" id="ccUsd"></div><div class="brk" id="ccBrk"></div><div class="note">프롬프트 캐싱·배치 할인으로 실제 비용은 더 낮아질 수 있어요. (환율 약 ₩'+KRW.toLocaleString()+' 가정, 토큰→글자수는 대략치)</div></div>';
  const sel=pgc.querySelector('#ccModel');
  Object.entries(M).forEach(([id,v])=>{const o=document.createElement('option');o.value=id;o.textContent=v[2]+' — '+v[3];sel.appendChild(o);});
  sel.value='claude-opus-5';
  const req=pgc.querySelector('#ccReq'), ti=pgc.querySelector('#ccIn'), to=pgc.querySelector('#ccOut'), pre=pgc.querySelector('#ccPre');
  const chars=t=>'약 '+Math.round(t*1.5).toLocaleString()+'자';   // 대략 한글 글자수
  function calc(){
    const m=M[sel.value], n=+req.value, i=+ti.value, o=+to.value;
    pgc.querySelector('#ccReqV').textContent=n+'회 / 일';
    pgc.querySelector('#ccInV').textContent=chars(i);
    pgc.querySelector('#ccOutV').textContent=chars(o);
    const per=(i/1e6*m[0])+(o/1e6*m[1]), day=per*n;
    pgc.querySelector('#ccKrw').textContent='하루 약 ₩'+Math.round(day*KRW).toLocaleString();
    pgc.querySelector('#ccUsd').textContent='≈ $'+day.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})+' / 일';
    pgc.querySelector('#ccBrk').innerHTML='요청 1건당 <b>약 ₩'+Math.round(per*KRW).toLocaleString()+'</b> · 한 달(30일) <b>약 ₩'+Math.round(day*KRW*30).toLocaleString()+'</b>';
  }
  Object.entries(P).forEach(([name,[pi,po,pn]])=>{const b=document.createElement('button');b.type='button';b.textContent=name;b.addEventListener('click',()=>{ti.value=pi;to.value=po;req.value=pn;[...pre.children].forEach(c=>c.classList.remove('on'));b.classList.add('on');calc();});pre.appendChild(b);});
  [sel,req,ti,to].forEach(e=>e.addEventListener('input',()=>{[...pre.children].forEach(c=>c.classList.remove('on'));calc();}));
  calc();
}

// ===== 이용약관 · 개인정보처리방침 · 저장소 설정 =====
const legalModal=document.getElementById('legalModal');
const legalTitle=document.getElementById('legalTitle');
const LEGAL_NAMES={terms:'이용약관',privacy:'개인정보처리방침',storage:'저장소 설정'};
let legalPrevFocus=null;

function showLegal(tab){
  legalModal.querySelectorAll('.legal-pane').forEach(p=>p.hidden = p.dataset.pane!==tab);
  legalModal.querySelectorAll('.legal-tabs button').forEach(b=>b.classList.toggle('on',b.dataset.tab===tab));
  legalTitle.textContent=LEGAL_NAMES[tab]||'';
  legalModal.querySelector('.legal-body').scrollTop=0;
  if(tab==='storage') renderPrefs();
}
function openLegal(tab){
  legalPrevFocus=document.activeElement;
  showLegal(tab);
  legalModal.classList.add('open');
  document.getElementById('legalClose').focus();
}
function closeLegal(){
  legalModal.classList.remove('open');
  if(legalPrevFocus&&legalPrevFocus.focus) legalPrevFocus.focus();
}
// 모달이 열려 있는 동안 Tab 포커스가 뒤 페이지로 새지 않도록 가둔다
const FOCUSABLE='a[href],button:not([disabled]):not([hidden]),input,select,textarea,[tabindex]:not([tabindex="-1"])';
function trapFocus(e){
  if(e.key!=='Tab') return;
  const box=[legalModal,sModal].find(m=>m.classList.contains('open'));
  if(!box) return;
  const items=[...box.querySelectorAll(FOCUSABLE)].filter(el=>el.offsetParent!==null);
  if(!items.length) return;
  const first=items[0], last=items[items.length-1];
  if(e.shiftKey && document.activeElement===first){ e.preventDefault(); last.focus(); }
  else if(!e.shiftKey && document.activeElement===last){ e.preventDefault(); first.focus(); }
  else if(!box.contains(document.activeElement)){ e.preventDefault(); first.focus(); }
}
document.addEventListener('keydown',trapFocus);

document.querySelectorAll('[data-legal]').forEach(b=>b.addEventListener('click',()=>openLegal(b.dataset.legal)));
legalModal.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>showLegal(b.dataset.tab)));
document.getElementById('legalClose').addEventListener('click',closeLegal);
legalModal.addEventListener('click',e=>{ if(e.target===legalModal) closeLegal(); });
document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&legalModal.classList.contains('open')) closeLegal(); });
// ?legal=terms 처럼 열린 상태로 공유할 수 있게 한다
(function(){
  const t=new URLSearchParams(location.search).get('legal');
  if(t&&LEGAL_NAMES[t]) openLegal(t);
})();

// --- 저장소 설정 스위치 ---
function renderPrefs(){
  legalModal.querySelectorAll('.sw[data-pref]').forEach(sw=>{
    sw.setAttribute('aria-checked', prefs[sw.dataset.pref]?'true':'false');
  });
  const kept=[];
  Object.entries(STORE_KEYS).concat([['prefs',PREF_KEY]]).forEach(([,k])=>{
    let v=null; try{ v=localStorage.getItem(k); }catch(_){}
    if(v!=null) kept.push(k+' ('+v.length+'자)');
  });
  document.getElementById('swState').innerHTML = kept.length
    ? '현재 이 브라우저에 저장된 항목: <b>'+kept.join('</b>, <b>')+'</b>'
    : '현재 이 브라우저에 저장된 항목이 없습니다.';
}
function setPref(name,on){
  prefs[name]=on;
  savePrefs();
  const key=STORE_KEYS[name];
  if(!on){
    try{ localStorage.removeItem(key); }catch(_){}
    if(name==='progress'){ readSet.clear(); renderProgress(); }
    if(name==='quiz'){
      for(const k in quizState) delete quizState[k];
      document.querySelectorAll('.quiz-q').forEach(clearQuizQ);
      document.querySelectorAll('.quiz-retry').forEach(b=>b.hidden=true);
      renderQuizChip(); renderProgress();
    }
  }else{
    // 다시 켜면 지금 상태부터 저장한다
    if(name==='theme'){ try{ localStorage.setItem('cc-theme',root.getAttribute('data-theme')); }catch(_){} }
    if(name==='progress') LSset('cc_read',[...readSet]);
    if(name==='quiz') LSset('cc_quiz',quizState);
    renderProgress();
  }
  renderPrefs();
}
legalModal.querySelectorAll('.sw[data-pref]').forEach(sw=>{
  sw.addEventListener('click',()=>setPref(sw.dataset.pref, sw.getAttribute('aria-checked')!=='true'));
});
document.getElementById('swClearAll').addEventListener('click',()=>{
  if(!confirm('이 브라우저에 저장된 진도·퀴즈·테마·설정값을 모두 삭제합니다. 계속할까요?')) return;
  Object.values(STORE_KEYS).concat([PREF_KEY]).forEach(k=>{ try{localStorage.removeItem(k);}catch(_){} });
  readSet.clear();
  for(const k in quizState) delete quizState[k];
  document.querySelectorAll('.quiz-q').forEach(clearQuizQ);
  document.querySelectorAll('.quiz-retry').forEach(b=>b.hidden=true);
  Object.assign(prefs,{theme:true,progress:true,quiz:true,ack:true});
  savePrefs();
  renderQuizChip(); renderProgress(); restartTop(); renderPrefs();
});

// 인쇄 전에 모달·배너를 닫아 둔다(열려 있으면 지면 첫 장을 가린다)
document.getElementById('printBtn')?.addEventListener('click',()=>{
  closeLegal(); closeSearch(); consentEl.classList.remove('show');
  window.print();
});

// --- 최초 방문 안내 ---
const consentEl=document.getElementById('consent');
function ackConsent(){ prefs.ack=true; savePrefs(); consentEl.classList.remove('show'); }
if(!prefs.ack) consentEl.classList.add('show');
document.getElementById('consentOk').addEventListener('click',ackConsent);
document.getElementById('consentPrefs').addEventListener('click',()=>{ ackConsent(); openLegal('storage'); });
</script>
</body>
</html>"""

if __name__ == "__main__":
    build()
