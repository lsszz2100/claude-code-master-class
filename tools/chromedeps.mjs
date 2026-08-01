/**
 * Playwright 가 쓸 시스템 라이브러리 경로를 스크립트가 스스로 챙긴다.
 *
 * 무인 sudo 가 안 되는 환경이라 libnspr4 같은 브라우저 의존 라이브러리를
 * ~/.local/chromedeps/root/ 밑에 풀어 두고 LD_LIBRARY_PATH 로 가리킨다.
 * 그런데 이걸 깜빡하면 실패가 조용하다 — Chromium 이 exit 127(공유 라이브러리 없음)로
 * 죽는데 로그 꼬리에는 `kill ESRCH` 같은 정리 메시지만 남아 원인이 안 드러난다.
 * prerender.mjs 의 경우엔 index.html 이 후처리 안 된 307KB 상태로 남고, 그대로 배포해도
 * jsdelivr CDN 폴백으로 "동작은 하므로" 한참 뒤에야 알아챈다.
 *
 * 그래서 경로가 있으면 붙여서 스크립트 자신을 다시 실행한다.
 * (환경 변수는 실행 중인 프로세스의 동적 링커에 소급 적용되지 않으므로 재실행 말고는 방법이 없다.)
 *
 * 아무것도 없는 환경(다른 머신·CI)에서는 조용히 통과한다 — 거기선 시스템 라이브러리를 쓴다.
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

// 경로는 환경마다 다르다. 있는 것만 쓴다 — 예전에 두 곳으로 적어 뒀지만
// 이 WSL 에 실제로 존재하는 건 root/usr/lib 쪽 하나뿐이다.
const DEPS = [
  path.join(os.homedir(), '.local/chromedeps/root/usr/lib/x86_64-linux-gnu'),
  path.join(os.homedir(), '.local/chromedeps/root/lib/x86_64-linux-gnu'),
].filter(d => fs.existsSync(d));

const FLAG = 'CC_CHROMEDEPS';   // 재실행 무한 반복 방지

export function ensureChromeDeps() {
  if (process.env[FLAG] || !DEPS.length) return;
  if ((process.env.LD_LIBRARY_PATH || '').includes(DEPS[0])) return;
  const r = spawnSync(process.execPath, [process.argv[1], ...process.argv.slice(2)], {
    stdio: 'inherit',
    env: { ...process.env, [FLAG]: '1',
      LD_LIBRARY_PATH: [...DEPS, process.env.LD_LIBRARY_PATH].filter(Boolean).join(':') },
  });
  process.exit(r.status ?? 1);
}
