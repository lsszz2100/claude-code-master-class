/**
 * 회귀 검증 — 빌드된 index.html 의 동작을 헤드리스 Chromium 으로 확인한다.
 *
 *   node tools/regress.mjs                 # 로컬 index.html (내장 정적 서버로 서빙)
 *   node tools/regress.mjs --url https://claude-code-tutorial-ko.vercel.app
 *   node tools/regress.mjs --keep-pdf      # 인쇄 검사가 만든 PDF 를 지우지 않음
 *
 * 검사 14건 + CDP Performance.getMetrics 지표.
 *
 * 왜 있나
 *   .chapter 는 content-visibility:auto 라서 뷰포트 밖 챕터가 "추정 높이"만 차지한다.
 *   추정값(#cv-sizes)은 tools/prerender.mjs 가 콘텐츠를 실측해 넣는데, 콘텐츠가 바뀌면
 *   값이 흔들리고 navTo 의 smooth scroll 이 목표를 조용히 빗나간다. 눈으로는 안 보이고
 *   배포 후에야 드러나므로 이동 도착 정확도를 기계로 재야 한다.
 *
 * 주의
 *   - 내장 서버는 gzip 을 하지 않는다. 네트워크 스로틀을 건 수치는 여기서 재면 안 되고
 *     (780KB 원본 전송에 묶여 개선 전후가 똑같이 나온다) --url 로 라이브에서 재야 한다.
 *   - Playwright 시스템 라이브러리 경로(LD_LIBRARY_PATH)는 이 스크립트가 알아서 챙긴다.
 */
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const SELF = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(SELF), '..');

// ── LD_LIBRARY_PATH 자기 처리 ───────────────────────────────────────
// 이게 없으면 Chromium 이 exit 127(공유 라이브러리 없음)로 죽는데, 로그 꼬리에는
// 정리 메시지만 남아 원인이 안 드러난다. 경로가 있으면 붙여서 자신을 다시 실행한다.
// (경로는 환경마다 다르다 — 있는 것만 골라 쓴다. 이 WSL 에는 root/usr/lib 쪽만 있다.)
const DEPS = [
  path.join(os.homedir(), '.local/chromedeps/root/usr/lib/x86_64-linux-gnu'),
  path.join(os.homedir(), '.local/chromedeps/root/lib/x86_64-linux-gnu'),
].filter(d => fs.existsSync(d));
if (!process.env.CC_REGRESS_REEXEC && DEPS.length
    && !(process.env.LD_LIBRARY_PATH || '').includes(DEPS[0])) {
  const r = spawnSync(process.execPath, [SELF, ...process.argv.slice(2)], {
    stdio: 'inherit',
    env: { ...process.env, CC_REGRESS_REEXEC: '1',
      LD_LIBRARY_PATH: [...DEPS, process.env.LD_LIBRARY_PATH].filter(Boolean).join(':') },
  });
  process.exit(r.status ?? 1);
}

const argv = process.argv.slice(2);
const urlArg = (argv.find(a => a.startsWith('--url')) || '').replace(/^--url=?/, '')
  || (argv[argv.indexOf('--url') + 1] || '').replace(/^--.*/, '');
const KEEP_PDF = argv.includes('--keep-pdf');

// 헤더 고정폭. build_course.py 의 scroll-margin-top 과 맞춰야 한다.
const ANCHOR_TOP = 72;
const ANCHOR_TOL = 40;          // 이 범위를 벗어나면 #cv-sizes 추정이 깨진 것
const LAYOUT_OBJECTS_MAX = 5000; // content-visibility 적용 후 실측 1,243 (적용 전 11,340)

// ── 내장 정적 서버 ──────────────────────────────────────────────────
const MIME = { '.html': 'text/html; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.xml': 'application/xml', '.txt': 'text/plain; charset=utf-8', '.ico': 'image/x-icon' };
let server = null, BASE = urlArg;
if (!BASE) {
  server = http.createServer((req, res) => {
    const rel = decodeURIComponent(req.url.split('?')[0]);
    const file = path.join(ROOT, rel === '/' ? 'index.html' : rel);
    if (!file.startsWith(ROOT) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      res.writeHead(404).end('not found'); return;
    }
    res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  await new Promise(ok => server.listen(0, '127.0.0.1', ok));
  BASE = `http://127.0.0.1:${server.address().port}/`;
}

const browser = await chromium.launch();

// ── 공통 픽스처 ─────────────────────────────────────────────────────
// 검사마다 새 컨텍스트를 쓴다 — 진도(localStorage)가 검사끼리 새면 결과를 못 믿는다.
async function open({ width = 1280, height = 900 } = {}) {
  const ctx = await browser.newContext({ viewport: { width, height } });
  const page = await ctx.newPage();
  const external = [], errors = [];
  page.on('request', r => {
    const u = r.url();
    if (/^https?:/.test(u) && !u.startsWith(BASE)) external.push(u);
  });
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push(String(e)));
  page.on('dialog', d => d.accept());      // 진도 초기화의 confirm()
  await page.goto(BASE, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  // 최초 방문 안내 배너는 반드시 #consentOk 로 닫아야 한다
  // (첫 버튼 #consentPrefs 는 법적 모달을 연다).
  await page.click('#consentOk');
  return { ctx, page, external, errors };
}

// 스크롤이 멈출 때까지 기다린다. smooth scroll 은 거리에 따라 2초를 넘긴다.
const settle = (page, timeout = 5000) => page.evaluate(t => new Promise(res => {
  let last = -1, still = 0; const t0 = performance.now();
  (function tick() {
    const y = window.scrollY;
    if (y === last) { if (++still >= 3) return res(y); } else { still = 0; last = y; }
    if (performance.now() - t0 > t) return res(y);
    requestAnimationFrame(tick);
  })();
}), timeout);

// 앵커가 화면 어디에 도착했는지 (기대값 ANCHOR_TOP)
const topOf = (page, id) => page.evaluate(
  i => document.getElementById(i).getBoundingClientRect().top, id);

const sleep = ms => new Promise(r => setTimeout(r, ms));

// 목차의 챕터 링크 id 들. 맨 위(#top)는 .chapter 가 아니라 scroll-margin-top 이 없으므로
// 도착 기대값이 다르다 — 정확도 검사 대상에서 뺀다.
const chapterIds = page => page.$$eval('.toc-ch', as => as
  .map(a => a.getAttribute('href').slice(1))
  .filter(id => document.getElementById(id)?.classList.contains('chapter')));

// ── 러너 ────────────────────────────────────────────────────────────
const results = [];
async function check(name, fn, opts) {
  const f = await open(opts);
  const notes = [];
  try {
    await fn({ ...f, note: s => notes.push(s) });
    results.push({ name, ok: true, notes });
    console.log(`  ✓ ${name}${notes.length ? '  — ' + notes.join(' · ') : ''}`);
  } catch (e) {
    results.push({ name, ok: false, notes, err: e.message });
    console.log(`  ✗ ${name}\n      ${e.message}${notes.length ? '\n      (' + notes.join(' · ') + ')' : ''}`);
  } finally {
    await f.ctx.close();
  }
}
function expect(cond, msg) { if (!cond) throw new Error(msg); }
function near(actual, want, tol, label) {
  expect(Math.abs(actual - want) <= tol,
    `${label}: ${Math.round(actual)}px (기대 ${want}±${tol}px, 오차 ${Math.round(actual - want)}px)`);
}

console.log(`\n대상: ${BASE}${server ? '  (내장 서버 — 네트워크 스로틀 측정용 아님)' : ''}\n`);

// 1. 런타임 외부 요청 0건 — prerender 가 CDN 의존을 없앴는지
await check('런타임 외부 요청 0건', async ({ page, external }) => {
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 900) {
      window.scrollTo({ top: y, behavior: 'instant' });
      await new Promise(r => requestAnimationFrame(r));
    }
  });
  await sleep(300);
  expect(external.length === 0, `외부 요청 ${external.length}건: ${external.slice(0, 3).join(', ')}`);
});

// 2. 콘솔·페이지 에러 0건
await check('콘솔·페이지 에러 0건', async ({ page, errors }) => {
  await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' }));
  await sleep(400);
  expect(errors.length === 0, `에러 ${errors.length}건: ${errors.slice(0, 2).join(' | ')}`);
});

// 3. 프리렌더 산출물 무결성 — 이중 실행이면 코드 블록이 조용히 깨진다
await check('프리렌더 산출물 무결성', async ({ page, note }) => {
  const r = await page.evaluate(() => ({
    mmd: document.querySelectorAll('figure.mmd').length,
    dark: document.querySelectorAll('figure.mmd .mmd-dark svg').length,
    light: document.querySelectorAll('figure.mmd .mmd-light svg').length,
    hljs: document.querySelectorAll('.content pre code [class^="hljs-"]').length,
    // 이중 실행의 진짜 증상: 이미 강조된 <span> 이 다시 이스케이프돼 본문에 노출된다
    leaked: document.body.innerText.includes('<span class="hljs-'),
  }));
  expect(r.mmd > 0, 'mermaid 도표가 하나도 없음 — 프리렌더를 건너뛴 빌드');
  expect(r.dark === r.mmd && r.light === r.mmd,
    `도표 ${r.mmd}개 중 다크 ${r.dark} / 라이트 ${r.light} — 두 벌이 다 있어야 함`);
  expect(r.hljs > 0, '코드 하이라이트 span 이 없음');
  expect(!r.leaked, 'prerender 이중 실행 흔적: 본문에 &lt;span class="hljs- 가 노출됨');
  note(`도표 ${r.mmd}개 · 강조 ${r.hljs}개`);
});

// 4. 목차 → 챕터 이동 도착 정확도
await check('목차 챕터 이동 도착 정확도', async ({ page, note }) => {
  const ids = await chapterIds(page);
  const pick = [ids[0], ids[Math.floor(ids.length / 3)], ids[Math.floor(ids.length * 2 / 3)], ids.at(-1)];
  const off = [];
  for (const id of pick) {
    await page.click(`.toc-ch[href="#${id}"]`);
    await settle(page);
    const top = await topOf(page, id);
    off.push(`${id} ${Math.round(top - ANCHOR_TOP) >= 0 ? '+' : ''}${Math.round(top - ANCHOR_TOP)}`);
    near(top, ANCHOR_TOP, ANCHOR_TOL, `${id} 도착`);
  }
  note(`오차 ${off.join(', ')}px`);
});

// 5. 목차 → 소제목 이동 도착 정확도
await check('목차 소제목 이동 도착 정확도', async ({ page, note }) => {
  const groups = page.locator('.toc-group.has-subs');
  const n = await groups.count();
  expect(n > 0, '소제목이 있는 목차 그룹이 없음');
  const g = groups.nth(Math.floor(n * 0.6));
  await g.locator('.toc-ch').click();                 // 접힌 그룹을 먼저 펼친다
  await sleep(400);
  const subs = g.locator('.toc-sub');
  const sub = subs.nth(Math.min(1, await subs.count() - 1));
  const href = await sub.getAttribute('href');
  await sub.click();
  await settle(page);
  const top = await topOf(page, decodeURIComponent(href.slice(1)));
  near(top, ANCHOR_TOP, ANCHOR_TOL, `${href} 도착`);
  note(`${href} 오차 ${Math.round(top - ANCHOR_TOP)}px`);
});

// 6. 위로 훑은 뒤 재이동 드리프트
// 챕터를 한 번 렌더하고 나면 contain-intrinsic-size:auto 가 실제 높이를 기억한다.
// 훑기 전후로 이동 결과가 달라지면 추정 높이가 실제와 어긋난 것이다.
await check('위로 훑은 뒤 재이동 드리프트', async ({ page, note }) => {
  const ids = await chapterIds(page);
  const target = ids[Math.floor(ids.length * 0.75)];
  await page.click(`.toc-ch[href="#${target}"]`);
  await settle(page);
  const before = await topOf(page, target);
  await page.evaluate(async () => {                    // 맨 아래까지 갔다가 위로 훑어 올린다
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' });
    await new Promise(r => requestAnimationFrame(r));
    for (let y = document.body.scrollHeight; y > 0; y -= 1200) {
      window.scrollTo({ top: y, behavior: 'instant' });
      await new Promise(r => requestAnimationFrame(r));
    }
    window.scrollTo({ top: 0, behavior: 'instant' });
  });
  await sleep(300);
  await page.click(`.toc-ch[href="#${target}"]`);
  await settle(page);
  const after = await topOf(page, target);
  near(after, ANCHOR_TOP, ANCHOR_TOL, `${target} 훑은 뒤 도착`);
  note(`${target} 훑기 전 ${Math.round(before - ANCHOR_TOP)} → 후 ${Math.round(after - ANCHOR_TOP)}px`);
});

// 7. 스크롤 스파이 — 현재 챕터 강조
await check('스크롤 스파이 (현재 챕터)', async ({ page }) => {
  const ids = await chapterIds(page);
  const id = ids[Math.floor(ids.length / 2)];
  await page.evaluate(i => {                           // navTo 를 안 거쳐야 스파이가 스스로 판정한다
    const el = document.getElementById(i);
    window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 60, behavior: 'instant' });
  }, id);
  await sleep(400);
  const active = await page.$eval('.toc-ch.active', a => a.getAttribute('href')).catch(() => null);
  expect(active === `#${id}`, `강조된 챕터가 ${active} (기대 #${id})`);
});

// 8. 소제목 강조 — 현재 챕터 안에서만 찾는지
await check('스크롤 스파이 (소제목 강조)', async ({ page, note }) => {
  const groups = page.locator('.toc-group.has-subs');
  const g = groups.nth(Math.floor((await groups.count()) * 0.5));
  await g.locator('.toc-ch').click();
  await sleep(400);
  const subs = g.locator('.toc-sub');
  const sub = subs.nth(Math.min(1, await subs.count() - 1));
  const href = await sub.getAttribute('href');
  await sub.click();
  await settle(page);
  await sleep(900);          // navTo 의 suppressSpy(650ms) 가 풀린 뒤 스파이가 다시 판정한다
  const active = await page.$eval('.toc-sub.active', a => a.getAttribute('href')).catch(() => null);
  expect(active === href, `강조된 소제목이 ${active} (기대 ${href})`);
  note(href);
});

// 9. 검색 → 제목 히트 이동
await check('검색 제목 히트 이동', async ({ page, note }) => {
  const q = await page.$$eval('.toc-ch', as => {
    const t = as[Math.floor(as.length * 0.7)];
    return (t.textContent || '').replace(/^\s*\d+\s*/, '').trim().slice(0, 6);
  });
  await page.keyboard.press('Control+k');
  await page.waitForSelector('#searchModal.open');
  await page.fill('#searchInput', q);
  await sleep(200);
  const href = await page.$eval('#searchResults a', a => a.getAttribute('href'));
  await page.keyboard.press('Enter');
  await settle(page);
  const top = await topOf(page, decodeURIComponent(href.slice(1)));
  near(top, ANCHOR_TOP, ANCHOR_TOL, `"${q}" → ${href} 도착`);
  note(`"${q}" → ${href} 오차 ${Math.round(top - ANCHOR_TOP)}px`);
});

// 10. 검색 → 본문 히트 이동 + 강조
// 본문 히트는 id 가 없는 블록으로 직접 이동하므로 block:'center' 이고, 강조(hit-flash)는
// 스크롤이 멈춘 뒤에 걸린다(먼 거리 이동은 2초 넘게 걸려 즉시 걸면 안 보인다).
await check('검색 본문 히트 이동 + 강조', async ({ page, note }) => {
  // 제목에는 없을 법한 본문 문구를 실제 문서에서 골라 검색어로 쓴다
  const q = await page.evaluate(() => {
    const ps = [...document.querySelectorAll('.content p')].filter(p => p.textContent.trim().length > 60);
    const p = ps[Math.floor(ps.length * 0.55)];
    return p.textContent.trim().slice(12, 22);
  });
  await page.keyboard.press('Control+k');
  await page.waitForSelector('#searchModal.open');
  await page.fill('#searchInput', q);
  await sleep(250);
  const idx = await page.$$eval('#searchResults a',
    as => as.findIndex(a => a.querySelector('.r-num')?.textContent.trim() === '¶'));
  expect(idx >= 0, `"${q}" 로 본문 히트가 안 나옴`);
  await page.locator('#searchResults a').nth(idx).click();
  await page.waitForSelector('.hit-flash', { timeout: 5000 });
  const box = await page.$eval('.hit-flash', el => {
    const r = el.getBoundingClientRect();
    return { center: r.top + r.height / 2, vh: window.innerHeight };
  });
  expect(box.center > 0 && box.center < box.vh,
    `강조된 블록이 화면 밖 (center ${Math.round(box.center)}px / vh ${box.vh})`);
  note(`"${q}" · 중앙에서 ${Math.round(box.center - box.vh / 2)}px`);
});

// 11. 읽음 진도 — 끝까지 내리면 전 챕터 기록
await check('읽음 진도 전 챕터 기록', async ({ page, note }) => {
  const total = await page.evaluate(() => document.querySelectorAll('.chapter').length);
  await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' }));
  await sleep(500);
  const read = await page.evaluate(() => JSON.parse(localStorage.getItem('cc_read') || '[]').length);
  const label = await page.$eval('#readProgress', el => el.textContent.replace(/\s+/g, ' ').trim());
  expect(read === total, `기록 ${read}/${total}`);
  expect(label.includes(`${total}/${total}`), `진도 표시가 "${label}"`);
  note(`${read}/${total}`);
});

// 12. 진도 초기화 → 즉시 맨 위, 재기록 없음
// scrollTo({behavior:'auto'}) 는 CSS scroll-behavior:smooth 를 따라 8만px 를 천천히 올라갔고,
// 그 사이 스크롤 핸들러가 진도를 다시 기록해 삭제가 무효화된 적이 있다. 반드시 'instant'.
await check('진도 초기화 → 즉시 맨 위 · 재기록 없음', async ({ page, note }) => {
  await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'instant' }));
  await sleep(400);
  await page.click('#rpReset');
  await sleep(120);
  const y0 = await page.evaluate(() => window.scrollY);
  expect(y0 === 0, `초기화 직후 scrollY=${Math.round(y0)} — 즉시 이동이 아님(smooth 로 새고 있음)`);
  await sleep(700);
  const after = await page.evaluate(() => ({
    y: window.scrollY, read: JSON.parse(localStorage.getItem('cc_read') || '[]').length }));
  expect(after.y === 0, `잠시 뒤 scrollY=${Math.round(after.y)}`);
  expect(after.read === 0, `초기화 뒤에도 진도 ${after.read}건이 다시 기록됨`);
  note('scrollY 0 유지 · 기록 0건');
});

// 13. 인쇄 — 전체 펼침 + PDF 생성
await check('인쇄 전체 펼침 + PDF 생성', async ({ page, note }) => {
  await page.emulateMedia({ media: 'print' });
  const cv = await page.$$eval('.chapter', cs =>
    [...new Set(cs.map(c => getComputedStyle(c).contentVisibility))]);
  expect(cv.every(v => v === 'visible'),
    `인쇄에서 content-visibility 가 ${cv.join('/')} — 건너뛴 챕터가 빈 페이지로 나간다`);
  const pdf = path.join(os.tmpdir(), 'cc-regress.pdf');
  await page.pdf({ path: pdf, format: 'A4', printBackground: false });
  const size = fs.statSync(pdf).size;
  expect(size > 50_000, `PDF 가 ${size}B — 본문이 안 실린 듯`);
  note(`PDF ${(size / 1024 / 1024).toFixed(1)}MB${KEEP_PDF ? ` (${pdf})` : ''}`);
  if (!KEEP_PDF) fs.unlinkSync(pdf);
  await page.emulateMedia({ media: 'screen' });
});

// 14. 모바일 상단바 버튼 겹침
// 존재 여부·스크린샷으로는 안 잡힌다 — 검색 버튼이 z-index 높은 테마 버튼에 완전히
// 가려져 클릭이 전부 테마 토글로 간 적이 있다. 클릭이 실제로 어디로 가는지 봐야 한다.
await check('모바일 상단바 버튼 클릭 겹침', async ({ page, note }) => {
  const hit = await page.evaluate(() => {
    const out = {};
    for (const id of ['searchBtnM', 'themeBtnM', 'menuBtn']) {
      const el = document.getElementById(id);
      if (!el) { out[id] = 'MISSING'; continue; }
      const r = el.getBoundingClientRect();
      const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      out[id] = !at ? 'NONE' : (el.contains(at) ? 'ok' : (at.id || at.className || at.tagName));
    }
    return out;
  });
  const bad = Object.entries(hit).filter(([, v]) => v !== 'ok');
  expect(bad.length === 0, bad.map(([k, v]) => `${k} 클릭이 "${v}" 로 감`).join(', '));
  note(Object.keys(hit).join(', '));
}, { width: 390, height: 844 });

// ── 성능 지표 (CDP) ─────────────────────────────────────────────────
// 로드 직후 값이다. content-visibility 의 이득은 여기서 나온다 — 스크롤로 전부
// 렌더한 뒤 재면 의미가 없다. 값은 기기 성능에 따라 흔들리므로 LayoutObjects 만 문턱을 건다.
console.log('\n성능 지표 (로드 직후, CDP Performance.getMetrics)');
let metricsOk = true;
{
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  const client = await ctx.newCDPSession(page);
  await client.send('Performance.enable');
  await page.goto(BASE, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const { metrics } = await client.send('Performance.getMetrics');
  const m = Object.fromEntries(metrics.map(x => [x.name, x.value]));
  const ms = v => `${(v * 1000).toFixed(0)}ms`;
  console.log(`  LayoutObjects ${m.LayoutObjects}   Nodes ${m.Nodes}   RecalcStyleCount ${m.RecalcStyleCount}`);
  console.log(`  Layout ${ms(m.LayoutDuration)}   RecalcStyle ${ms(m.RecalcStyleDuration)}`
    + `   Script ${ms(m.ScriptDuration)}   Task ${ms(m.TaskDuration)}`);
  if (m.LayoutObjects > LAYOUT_OBJECTS_MAX) {
    metricsOk = false;
    console.log(`  ✗ LayoutObjects ${m.LayoutObjects} > ${LAYOUT_OBJECTS_MAX}`
      + ' — content-visibility 가 안 먹고 있다. 건너뛴 챕터의 레이아웃을 읽는 JS 가 생겼는지 확인.');
  } else {
    console.log(`  ✓ LayoutObjects ${m.LayoutObjects} ≤ ${LAYOUT_OBJECTS_MAX}`);
  }
  await ctx.close();
}

// ── 정리 ────────────────────────────────────────────────────────────
await browser.close();
if (server) server.close();

const failed = results.filter(r => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} 통과`
  + (failed.length ? ` — 실패: ${failed.map(f => f.name).join(', ')}` : '')
  + (metricsOk ? '' : ' · 성능 지표 회귀'));
process.exit(failed.length || !metricsOk ? 1 : 0);
