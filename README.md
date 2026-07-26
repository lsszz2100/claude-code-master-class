# Claude Code 마스터 클래스

> 설치부터 컨텍스트 엔지니어링·하네스까지, Claude Code를 한국어로 정리한 종합 실전 강의.

**라이브** → <https://claude-code-tutorial-ko.vercel.app>

17개 챕터, 15세트 45문항의 확인 퀴즈, 브라우저에서 바로 만져 보는 놀이터 3종, 수료증 생성까지
**단일 HTML 파일 하나**로 동작하는 정적 강의 사이트입니다.

> [!NOTE]
> 이 강의는 공개된 공식 문서를 참고해 집필한 **비공식 학습 자료**입니다.
> Anthropic PBC와 제휴·후원·승인 관계가 없으며, Claude 및 Claude Code는 Anthropic PBC의 상표입니다.

## 무엇이 들어 있나

| 구성 | 내용 |
|---|---|
| **강의 본문** | 설치·권한·모델·명령어·CLAUDE.md·자동 기억·서브에이전트·스킬·훅·MCP·오케스트레이션·컨텍스트 엔지니어링·하네스/루프·프롬프트 가이드 |
| **확인 퀴즈** | 챕터마다 3문항, 오답 시 정답과 해설 표시, 진도·점수는 브라우저에 저장 |
| **놀이터** | 슬래시 커맨드 터미널 시뮬레이터 · 확장 선택 진단기 · 모델 비용 계산기 |
| **수료증** | 이름을 넣어 PNG로 저장 (브라우저 안에서만 생성, 서버 전송 없음) |
| **본문 전문 검색** | `Ctrl`/`⌘` + `K` — 제목뿐 아니라 본문까지 검색하고 해당 문단으로 이동 |

## 저장소 구조

```
course-site/
├─ build_course.py      # 빌드 스크립트 — 이 파일 하나가 사이트 전체를 생성한다
├─ content/             # 강의 원고 (Markdown) — 실제로 고칠 곳은 여기
│  ├─ 01-intro-install.md
│  ├─ …
│  └─ 17-references.md
├─ index.html           # 빌드 산출물 (배포되는 파일, 커밋 대상)
├─ favicon.svg  apple-touch-icon.png  og.png
└─ .vercelignore        # 배포에는 index.html + 아이콘/OG만 올라간다
```

`index.html`은 **생성물**입니다. 직접 고치지 말고 `content/`와 `build_course.py`를 고친 뒤 다시 빌드하세요.

## 빌드

```bash
pip install markdown
python3 build_course.py      # content/*.md → index.html
```

로컬에서 확인:

```bash
python3 -m http.server 8899
# http://127.0.0.1:8899
```

## 배포

Vercel 정적 배포입니다.

```bash
npx vercel deploy --prod --yes
```

`build_course.py`와 `content/`는 `.vercelignore`로 배포에서 제외되며,
`index.html`과 아이콘·OG 이미지만 올라갑니다.

## 개인정보 · 저장 데이터

이 사이트는 **쿠키와 추적 도구를 사용하지 않습니다.** 분석 스크립트도 없습니다.
학습 편의를 위해 아래 항목만 브라우저 localStorage에 저장하며, 서버로 전송되지 않습니다.

| 키 | 내용 |
|---|---|
| `cc-theme` | 밝은/어두운 테마 선택 |
| `cc_read` | 읽은 챕터 목록 |
| `cc_quiz` | 퀴즈 문항별 선택 |
| `cc_prefs` | 위 항목의 저장 여부 설정 |

사이트 하단 **저장소 설정**에서 항목별로 끄거나 전부 삭제할 수 있습니다.

## 기여

내용 오류·오탈자 제보는 이슈로 남겨 주세요.
콘텐츠는 변경금지(ND) 라이선스라 **수정본 배포는 불가**하지만, 제보해 주시면 원본에 반영합니다.

## 라이선스

| 대상 | 라이선스 |
|---|---|
| 소스 코드 (`build_course.py` 등) | [MIT](LICENSE) |
| 강의 콘텐츠 (`content/`, `index.html` 본문, 이미지) | [CC BY-NC-ND 4.0](LICENSE-CONTENT.md) |

---

제작 · **AI_Innovation_Studio**
