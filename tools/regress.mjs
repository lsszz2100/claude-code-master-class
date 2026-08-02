/**
 * 회귀 검증 — 빌드된 index.html 의 동작을 헤드리스 Chromium 으로 확인한다.
 *
 *   node tools/regress.mjs                 # 로컬 index.html (내장 정적 서버로 서빙)
 *   node tools/regress.mjs --url https://claude-code-tutorial-ko.vercel.app
 *   node tools/regress.mjs --keep-pdf      # 인쇄 검사가 만든 PDF 를 지우지 않음
 *
 * 검사 18건 + CDP Performance.getMetrics 지표.
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
import { fileURLToPath } from 'node:url';
import { ensureChromeDeps } from './chromedeps.mjs';

ensureChromeDeps();   // LD_LIBRARY_PATH 를 챙겨 자신을 다시 실행할 수 있다 (첫 문장이어야 한다)

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

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
// 소스에는 jsdelivr 문자열이 4건 남아 있지만 전부 "후처리를 건너뛴 빌드"용 폴백이다.
// 문자열을 세는 것만으로는 죽은 코드인지 알 수 없으므로, 그 코드를 깨우는 조건 두 개가
// 실제로 거짓인지 보고 + 테마 전환(폴백이 CSS 를 갈아끼우는 지점)까지 태워서 확인한다.
await check('런타임 외부 요청 0건', async ({ page, external, note }) => {
  const guards = await page.evaluate(() => ({
    hljsLink: !!document.getElementById('hljs-theme'),          // 있으면 테마 전환 때 CDN CSS 를 받는다
    mermaidPre: document.querySelectorAll('pre.mermaid').length, // 있으면 mermaid 를 CDN 에서 받는다
  }));
  expect(!guards.hljsLink, '#hljs-theme <link> 가 살아 있음 — 인라인 <style> 로 대체됐어야 한다');
  expect(guards.mermaidPre === 0,
    `pre.mermaid ${guards.mermaidPre}개가 요소로 살아 있음 — 도표가 인라인 SVG 로 안 바뀌었다`);
  await page.evaluate(async () => {
    for (let y = 0; y < document.body.scrollHeight; y += 900) {
      window.scrollTo({ top: y, behavior: 'instant' });
      await new Promise(r => requestAnimationFrame(r));
    }
  });
  await page.click('#themeBtn');   // 다크 → 라이트
  await sleep(200);
  await page.click('#themeBtn');   // 라이트 → 다크
  await sleep(400);
  expect(external.length === 0, `외부 요청 ${external.length}건: ${external.slice(0, 3).join(', ')}`);
  note('스크롤 전체 + 테마 왕복 · 폴백 가드 2개 모두 거짓');
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

// 15. 접근성 기본
// 이런 결함은 화면으로는 절대 안 보인다 — 스크린리더에서만 드러나므로 기계로 지켜야 한다.
await check('접근성 기본 (접근 이름·모달·현재 위치)', async ({ page, note }) => {
  const a = await page.evaluate(() => {
    const named = el => !!(el.getAttribute('aria-label') || el.getAttribute('aria-labelledby')
      || (el.id && document.querySelector(`label[for="${el.id}"]`)) || el.closest('label'));
    const accName = el => (el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent || '').trim();
    return {
      lang: document.documentElement.lang,
      // placeholder 는 접근 이름이 아니다 — 입력 중에는 사라진다
      inputsUnnamed: [...document.querySelectorAll('input,select,textarea')]
        .filter(el => el.type !== 'hidden' && !named(el)).map(el => el.id || el.type),
      controlsUnnamed: [...document.querySelectorAll('button, a[href]')]
        .filter(el => !accName(el)).map(el => el.id || el.className).slice(0, 5),
      modals: ['searchModal', 'legalModal'].map(id => {
        const el = document.getElementById(id);
        return { id, ok: !!el && el.getAttribute('role') === 'dialog' && el.getAttribute('aria-modal') === 'true'
          && !!(el.getAttribute('aria-label') || el.getAttribute('aria-labelledby')) };
      }),
      // 진행 막대는 장식 — 같은 정보를 사이드바가 글로 준다
      progressHidden: document.getElementById('progress')?.getAttribute('aria-hidden') === 'true',
      // 도표는 인라인 SVG 라 대체 텍스트가 없으면 스크린리더가 통째로 건너뛴다
      figuresUnlabeled: [...document.querySelectorAll('figure.mmd')].filter(f => !f.getAttribute('aria-label')).length,
      skipLink: !!document.querySelector('.skip-link'),
      landmarks: ['main', 'nav', 'footer'].filter(t => !document.querySelector(t)),
    };
  });
  expect(a.lang === 'ko', `<html lang>가 "${a.lang}"`);
  expect(a.inputsUnnamed.length === 0, `접근 이름 없는 입력: ${a.inputsUnnamed.join(', ')}`);
  expect(a.controlsUnnamed.length === 0, `접근 이름 없는 버튼·링크: ${a.controlsUnnamed.join(', ')}`);
  const badModal = a.modals.filter(m => !m.ok).map(m => m.id);
  expect(badModal.length === 0, `role=dialog/aria-modal/이름이 빠진 모달: ${badModal.join(', ')}`);
  expect(a.progressHidden, '#progress 가 aria-hidden 이 아님 — 스크롤마다 접근성 트리가 흔들린다');
  expect(a.figuresUnlabeled === 0, `대체 텍스트 없는 도표 ${a.figuresUnlabeled}개`);
  expect(a.skipLink, '본문 건너뛰기 링크가 없음');
  expect(a.landmarks.length === 0, `빠진 랜드마크: ${a.landmarks.join(', ')}`);

  // 현재 챕터가 색 말고 의미로도 노출되는지
  const ids = await chapterIds(page);
  await page.click(`.toc-ch[href="#${ids[2]}"]`);
  await settle(page);
  await sleep(800);
  const cur = await page.$$eval('.toc-ch[aria-current]', as => as.map(a => a.getAttribute('href')));
  expect(cur.length === 1 && cur[0] === `#${ids[2]}`,
    `aria-current 가 ${JSON.stringify(cur)} (기대 ["#${ids[2]}"] 하나)`);
  note(`입력 ${'0'}건 미명명 · 모달 2 · aria-current ${cur[0]}`);
});

// ── 놀이터 위젯 ─────────────────────────────────────────────────────
// 세 위젯은 전부 JS 로 그려진다. 빌드가 통과해도 위젯 안에서 조용히 죽으면 페이지는
// 멀쩡해 보이고 챕터 15만 텅 빈다 — 눈으로 안 보므로 기계로 눌러 봐야 한다.

// 위젯은 #ch15 안이라 content-visibility 로 렌더가 건너뛰어져 있다. 클릭하려면 먼저 올려야 한다.
const reachPlayground = async page => {
  await page.locator('.pg-terminal').scrollIntoViewIfNeeded();
  await settle(page);
};

// 16. 터미널 놀이터 — 미션 · 히스토리 · 자동완성
await check('놀이터 터미널 (미션·히스토리·Tab 완성)', async ({ page, note }) => {
  await reachPlayground(page);
  const misText = () => page.$eval('#pgMis', el => el.textContent);
  const outText = () => page.$eval('#pgOut', el => el.textContent);
  const inVal = () => page.$eval('#pgIn', el => el.value);

  expect(/미션 1\s*\/\s*6/.test(await misText()), `미션 바가 1/6 로 시작하지 않음: ${await misText()}`);

  // 미션 1 의 정답을 치면 다음 미션으로 넘어가야 한다
  await page.click('#pgIn');
  await page.type('#pgIn', '/context');
  await page.keyboard.press('Enter');
  expect((await outText()).includes('미션 1 완료'), '정답을 쳤는데 미션 완료가 안 찍힘');
  expect(/미션 2\s*\/\s*6/.test(await misText()), `미션이 2/6 로 안 넘어감: ${await misText()}`);

  // 오답은 오답이라고 해야 한다 (아무거나 통과시키면 미션이 의미가 없다)
  await page.type('#pgIn', '/nope');
  await page.keyboard.press('Enter');
  expect((await outText()).includes('명령을 찾을 수 없습니다'), '없는 명령인데 오류가 안 나옴');
  expect(/미션 2\s*\/\s*6/.test(await misText()), '오답인데 미션이 넘어갔다');

  // Tab 자동완성 — /comp → /compact
  await page.type('#pgIn', '/comp');
  await page.keyboard.press('Tab');
  expect(await inVal() === '/compact', `Tab 완성 결과가 "${await inVal()}" (기대 /compact)`);
  expect(await page.evaluate(() => document.activeElement.id) === 'pgIn',
    'Tab 이 입력창에서 포커스를 빼앗겼다');

  // 입력이 비었을 때의 Tab 은 가로채면 안 된다 — 키보드로 빠져나갈 수 없게 된다
  await page.fill('#pgIn', '');
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => document.activeElement.id) !== 'pgIn',
    '빈 입력에서도 Tab 을 가로채 포커스가 갇혔다');

  // ↑ 히스토리
  await page.click('#pgIn');
  await page.keyboard.press('ArrowUp');
  expect(await inVal() === '/nope', `↑ 이 복원한 값이 "${await inVal()}" (기대 /nope)`);

  // Ctrl+L 화면 지우기
  await page.fill('#pgIn', '');
  await page.keyboard.press('Control+l');
  expect((await outText()).trim() === '', 'Ctrl+L 이 화면을 안 지움');

  const cmds = await page.$$eval('.pg-chips button', bs => bs.length);
  note(`미션 6개 · 칩 ${cmds}개`);
});

// 17. 확장 진단기 — 2단계 분기 · 스니펫 · 뒤로 가기
await check('놀이터 진단기 (분기·스니펫·뒤로)', async ({ page, note }) => {
  await reachPlayground(page);
  // 질문이 아예 없을 수도 있으므로(바로 결과로 튀는 회귀) null 을 허용해서 읽는다
  const q = () => page.evaluate(() => document.querySelector('.pg-wizard .pg-q')?.textContent ?? null);
  const first = await q();
  expect(first, '진단기가 첫 질문을 못 그림');

  // "무조건 매번 일어나야 한다" → 2단계로 갈라져야 한다 (예전에는 바로 결과였다)
  await page.click('.pg-wizard .pg-opts button:nth-child(3)');
  const second = await q();
  expect(second && second !== first, `2단계 질문으로 안 갈라짐 (지금: ${second ?? '질문 없이 결과로 직행'})`);
  expect((await page.$eval('.pg-wizard .pg-step', el => el.textContent)).includes('질문 2'),
    '단계 표시가 질문 2 가 아님');

  // "전에 막아야" → PreToolUse 결과 + 복사 가능한 스니펫
  await page.click('.pg-wizard .pg-opts button:nth-child(1)');
  const r = await page.evaluate(() => ({
    title: document.querySelector('.pg-wizard .pg-result h4')?.textContent || '',
    code: document.querySelector('.pg-wizard .pg-result pre code')?.textContent || '',
    copy: !!document.querySelector('.pg-wizard .pg-result .copy-btn'),
    also: !!document.querySelector('.pg-wizard .pg-also'),
  }));
  expect(r.title.includes('PreToolUse'), `결과 제목이 "${r.title}"`);
  expect(r.code.includes('PreToolUse') && r.code.length > 80, `스니펫이 비었거나 짧음 (${r.code.length}자)`);
  // 훅 스니펫은 9장의 방식(stdin JSON + jq)과 같아야 한다 — 여기서만 다른 관용구를 가르치면 안 된다
  expect(r.code.includes('jq'), '훅 스니펫이 stdin JSON(jq) 방식이 아님');
  expect(r.copy, '스니펫에 복사 버튼이 없음');
  expect(r.also, '보조 설명(.pg-also)이 없음');

  // 뒤로 → 2단계 질문으로 돌아가야 한다 (답 바꾸려고 처음부터 다시 하게 만들면 안 된다)
  await page.click('.pg-wizard .pg-nav button:nth-child(1)');
  expect(await page.$('.pg-wizard .pg-opts') !== null, '뒤로 눌렀는데 질문이 안 나옴');
  expect((await page.$eval('.pg-wizard .pg-step', el => el.textContent)).includes('질문 2'),
    `뒤로가 2단계가 아닌 곳으로 감`);

  note(`결과 "${r.title}" · 스니펫 ${r.code.length}자`);
});

// 18. 비용 계산기 — 캐싱·배치·모델 비교
// 값을 통째로 박아 두면 가격표가 정당하게 바뀔 때마다 깨진다. 가격과 무관한
// 관계(배치는 정확히 절반, 캐싱은 감소, 선택 모델 행 = 총액)만 건다.
await check('놀이터 계산기 (캐싱·배치·모델 비교)', async ({ page, note }) => {
  await reachPlayground(page);
  const won = () => page.$eval('#ccKrw', el => +el.textContent.replace(/[^\d]/g, ''));
  const setRange = (id, v) => page.$eval(id, (el, val) => {
    el.value = val; el.dispatchEvent(new Event('input', { bubbles: true }));
  }, v);

  const base = await won();
  expect(base > 0, `기본 상태에서 하루 비용이 ${base}`);

  await setRange('#ccHit', 80);
  const cached = await won();
  expect(cached < base, `캐시 80% 인데 비용이 안 줄었다 (${base} → ${cached})`);

  await page.click('#ccBatch');
  const batched = await won();
  // 반올림 오차 1원까지 허용
  expect(Math.abs(batched * 2 - cached) <= 2, `배치가 정확히 절반이 아니다 (${cached} → ${batched})`);

  await page.click('#ccBatch');
  await setRange('#ccHit', 0);
  expect(Math.abs(await won() - base) <= 1, '되돌렸는데 원래 값으로 안 돌아옴');

  // 모델 비교 막대
  const cmp = await page.evaluate(() => ({
    rows: [...document.querySelectorAll('.pg-cmp .row')].map(r => ({
      name: r.querySelector('.nm').textContent,
      won: +r.querySelector('.amt').textContent.replace(/[^\d]/g, ''),
      on: r.classList.contains('on'),
      width: parseFloat(r.querySelector('.bar i').style.width),   // CSSOM 이 "100.0%" 를 "100%" 로 정규화한다
    })),
    selected: document.querySelector('#ccModel').selectedOptions[0].textContent,
  }));
  expect(cmp.rows.length === 4, `비교 행이 ${cmp.rows.length}개 (기대 4)`);
  const on = cmp.rows.filter(r => r.on);
  expect(on.length === 1, `강조된 행이 ${on.length}개 (기대 1)`);
  expect(cmp.selected.startsWith(on[0].name), `강조 행 "${on[0].name}" 이 선택 모델 "${cmp.selected}" 과 다름`);
  expect(on[0].won === base, `강조 행 금액 ${on[0].won} 이 총액 ${base} 과 다름`);
  // 싼 모델이 비싼 모델보다 싸야 한다 — 가격표를 잘못 이어 붙이면 여기서 잡힌다
  const byName = Object.fromEntries(cmp.rows.map(r => [r.name, r.won]));
  expect(byName['Haiku 4.5'] < byName['Fable 5'], '모델 순서대로 비용이 오르지 않음');
  const widest = cmp.rows.reduce((a, b) => (b.won > a.won ? b : a));
  expect(Math.abs(widest.width - 100) < 0.05, `가장 비싼 모델의 막대가 ${widest.width}% (기대 100%)`);

  note(`하루 ₩${base.toLocaleString()} · 캐시80% ₩${cached.toLocaleString()} · 비교 4모델`);
});

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
