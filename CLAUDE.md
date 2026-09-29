# Claude Code Project Guidelines & Mandatory Rules

> 🚨 **사용자 절대 원칙: 허위보고 원천 금지 (Zero-Tolerance on False Reporting)**
> - **작업 안 한 것을 했다고 허위 보고하는 행위는 엄격히 금지된다.**
> - "추정", "완료된 것으로 간주", 실제 실행 없는 성공 보고는 일체 불가.
> - 모든 보고는 실제 실행된 커맨드 출력 로그, 실측된 수치(바이트 일치, px 오차, 통과 건수)를 기반으로 해야 한다.

## 5대 필수 검증 및 작업 의무
1. **무조건 실검증 (Practical Verification)**:
   - 빌드(`python3 build_course.py && node tools/prerender.mjs`) 및 회귀 테스트(`node tools/regress.mjs`) 직접 실행 및 전건 통과(`32/32 PASS`) 확인 필수.
2. **라이브 교차검증 (Cross-Validation)**:
   - 로컬과 라이브 HTML 바이트 레벨 일치 실측: `curl -s <배포URL> | cmp - index.html`
   - 배포 URL 대상 브라우저 실측: `node tools/regress.mjs --url <배포URL>`
3. **보안검증 (Security Verification)**:
   - XSS 방지 엔티티 새니타이징(`esc()`) 점검.
   - 보안 헤더(HSTS, CSP, nosniff 등) 응답 확인.
   - 런타임 외부 네트워크 요청 0건 유지.
4. **기능 테스트 및 버그/예외 테스트 (Functional & Bug Testing)**:
   - 정상 분기 및 예외/에러 분기 검증.
   - 음성 대조(Negative Testing)로 테스트 스위트의 신뢰성 검증.
   - 뷰포트 3종(1280px, 900px, 390px) 가로 넘침(Horizontal Overflow) 0px 검증.
5. **리팩토링 (Refactoring)**:
   - 코드 중복 제거, 명확한 네이밍, CSS/JS 아키텍처 정합성 유지, 기존 컴포넌트 충돌 방지.

---

## 프로젝트 메모리 및 핵심 컨텍스트 (Project Memory)

### 1. 최신 모델 표준 (2026년 9월 기준)
- **Claude Sonnet 5.5 (`claude-sonnet-5-5`)**:
  - 출시일: 2026년 9월 28일
  - 스펙: 1M 컨텍스트 창, 128K 최대 출력, 입력 $2/M, 출력 $10/M (캐시 쓰기 $2.50, 캐시 읽기 $0.20)
  - 벤치마크: Terminal-Bench 4.0 **70.6%**, GDPval-AA v2.1 1,844 Elo
  - 10대 공식 프롬프트 패턴([14장 3부](https://claude-code-tutorial-ko.vercel.app/#ch14)):
    1) Effort 재조정(에이전틱 코딩 `medium` 권장, `max_tokens` 128K)
    2) 자율성/범위 제어(조기 중단 방지, `xhigh`/`max` 자체 리뷰 남발 차단)
    3) between_tools 사고 제약(high 이하만 허용, 400 방지, 태그 유출 지침 제거)
    4) 정형 JSON 추론 유도("Think the problem through before you answer")
    5) 사용자 진행 알림(`display: "updates"`, 5회 침묵 시 리마인더)
    6) 지식 검색 도구 강제(최신 규정/요금 검색)
    7) 미드턴 메시지 격리(`tool_result` 내 사용자 텍스트 삽입 절대 금지, text 블록 Append)
    8) 코딩 실검증 강제(의존성 미비 핑계 차단)
    9) 관용적 도구 호출 수용(is_error 자체 교정)
    10) 복합 시각 입력(Crop/Zoom 도구) 및 5대 거부 카테고리 대응
- **Claude Opus 5.5 (`claude-opus-5-5`)**: 완료 기준(Done) 명시, "think carefully" 삭제, CLAUDE.md 스톱 규칙, TASKS.md 유지.
- **Claude Fable 5.1 (`claude-fable-5-1`)**: 캐시 읽기 $0.25/M 초저가, 4단계 Multi-Effort 루프, Append-only 컨텍스트 무결성.

### 2. 프로덕션 환경 및 파이프라인
- **라이브 URL**: [https://claude-code-tutorial-ko.vercel.app](https://claude-code-tutorial-ko.vercel.app)
- **Git 원격 저장소**: `origin main` (GitHub `lsszz2100/claude-code-master-class`)
- **표준 빌드/검증 파이프라인**:
  ```bash
  cd course-site
  python3 build_course.py && node tools/prerender.mjs
  node tools/regress.mjs                     # 로컬 32/32 PASS 필수
  git add -A && git commit -m "..." && git push origin main
  npx --yes vercel --prod --yes             # 프로덕션 배포
  curl -s <라이브URL> | cmp - index.html     # 0바이트 차이 실측
  node tools/regress.mjs --url <라이브URL>  # 라이브 32/32 PASS 필수
  ```
- **현재 산출물 기준**: `index.html` 1,061,642 바이트, 18개 챕터, 15개 mermaid 다이어그램(다크/라이트 30개 SVG), 회귀 검증 32개 전건 통과.
