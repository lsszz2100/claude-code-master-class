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
| **놀이터** | 슬래시 커맨드 터미널 시뮬레이터(미션 6개 · Tab 완성 · 히스토리) · 확장 선택 진단기(2단계 분기 + 복사 가능한 설정 스니펫) · 모델 비용 계산기(캐싱·배치 할인·모델 4종 비교) |
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
├─ tools/prerender.mjs  # 빌드 후처리 — 도표·코드 강조를 미리 렌더해 외부 CDN 의존을 없앤다
├─ tools/regress.mjs    # 회귀 검증 — 이동 정확도·검색·진도·인쇄·놀이터 등 18건 + 성능 지표
├─ tools/chromedeps.mjs # 위 두 스크립트가 쓰는 Chromium 라이브러리 경로 처리
├─ index.html           # 빌드 산출물 (배포되는 파일, 커밋 대상)
├─ robots.txt  sitemap.xml   # 빌드가 함께 생성한다
├─ favicon.svg  apple-touch-icon.png  og.png
└─ .vercelignore        # 배포에는 index.html + 아이콘/OG + robots/sitemap 만 올라간다
```

`index.html`은 **생성물**입니다. 직접 고치지 말고 `content/`와 `build_course.py`를 고친 뒤 다시 빌드하세요.

## 빌드

```bash
pip install markdown
python3 build_course.py       # content/*.md → index.html (+ robots.txt, sitemap.xml)
node tools/prerender.mjs      # 도표·코드 강조를 미리 렌더 → 런타임 외부 요청 0건
```

두 번째 단계는 Playwright(`npm i -D playwright`)가 필요합니다. 건너뛰어도 사이트는
jsDelivr CDN 폴백으로 동작하지만, 그만큼 첫 화면이 늦고 외부 요청이 생깁니다.
성공하면 로그에 `index.html 300KB → 761KB`가 찍힙니다 — 이게 안 보이면 후처리가
안 된 것이니 그대로 배포하지 마세요.

로컬에서 확인:

```bash
python3 -m http.server 8899
# http://127.0.0.1:8899
```

## 회귀 검증

빌드한 뒤 반드시 돌리세요. 내장 정적 서버로 `index.html`을 띄워 18건을 검사합니다.

```bash
node tools/regress.mjs                       # 로컬 빌드
node tools/regress.mjs --url https://…       # 배포된 사이트
```

검사 항목은 목차·검색 이동 도착 정확도(72±40px), 스크롤 스파이, 소제목 강조,
읽음 진도, 진도 초기화, 인쇄 전체 펼침 + PDF, 모바일 버튼 클릭 겹침,
런타임 외부 요청 0건, 프리렌더 산출물 무결성, 접근성 기본, 놀이터 위젯 3종이고,
끝에 CDP 성능 지표를 찍습니다.

특히 **이동 도착 정확도**가 핵심입니다. `.chapter`는 화면에서 `content-visibility:auto`라
뷰포트 밖 챕터가 `tools/prerender.mjs`가 실측해 넣은 추정 높이(`#cv-sizes`)만 차지하는데,
콘텐츠가 바뀐 뒤 이 값이 어긋나면 목차 이동이 엉뚱한 곳에 도착합니다. 눈에 잘 안 띄고
배포 후에야 드러나므로 기계로 재야 합니다.

> 내장 서버는 gzip을 하지 않습니다(780KB 원본을 그대로 보냄 — Vercel에서는 117KB).
> 네트워크 스로틀을 건 수치는 `--url`로 라이브에서 재세요.

## 배포

Vercel 정적 배포입니다.

```bash
npx vercel deploy --prod --yes
```

`build_course.py`와 `content/`는 `.vercelignore`로 배포에서 제외되며,
`index.html`과 아이콘·OG 이미지만 올라갑니다.

## 개인정보 · 저장 데이터

이 사이트는 **쿠키와 추적 도구를 사용하지 않습니다.** 분석 스크립트도 없고,
페이지를 여는 동안 **외부 서버로 나가는 요청이 하나도 없습니다**(도표·코드 강조를 빌드 시점에 미리 렌더).
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
