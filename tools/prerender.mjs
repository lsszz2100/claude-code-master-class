/**
 * 빌드 후처리 — 외부 CDN 의존을 제거한다.
 *
 *   python3 build_course.py && node tools/prerender.mjs
 *
 * 하는 일
 *   1. <pre class="mermaid"> 를 다크/라이트 두 벌의 인라인 SVG로 미리 렌더
 *   2. <pre><code> 를 highlight.js 로 미리 강조 (클래스만 남김)
 *   3. highlight.js 테마 CSS 두 개를 [data-theme] 로 스코프해 인라인
 *   4. jsDelivr 로 나가던 <link>/<script>/preconnect 제거
 *   5. 챕터별 실제 높이를 재서 contain-intrinsic-size 로 주입 (#cv-sizes)
 *
 * 결과: 런타임 외부 요청 0건. mermaid·hljs 는 이 스크립트가 도는 빌드 시점에만 받는다.
 * 이 단계를 건너뛰어도 사이트는 CDN 폴백으로 동작한다(느릴 뿐).
 *
 * 이 스크립트는 멱등이 아니다 — 반드시 build_course.py 의 출력에서 시작해야 한다.
 * 이미 후처리된 파일이면 아무것도 건드리지 않고 exit 1 한다(아래 "멱등성 가드").
 *
 * Playwright 시스템 라이브러리 경로(LD_LIBRARY_PATH)는 tools/chromedeps.mjs 가 챙긴다 —
 * 손으로 붙일 필요 없다. 빌드 뒤에는 node tools/regress.mjs 로 회귀 검사를 돌릴 것.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ensureChromeDeps } from './chromedeps.mjs';

ensureChromeDeps();   // LD_LIBRARY_PATH 를 챙겨 자신을 다시 실행할 수 있다 (첫 문장이어야 한다)

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const FILE = path.join(ROOT, 'index.html');
const MERMAID = 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
const HLJS = 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/highlight.min.js';
const HL_CSS = {
  dark: 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github-dark.min.css',
  light: 'https://cdn.jsdelivr.net/gh/highlightjs/cdn-release@11.9.0/build/styles/github.min.css',
};
const FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", "Malgun Gothic", sans-serif';

const decode = s => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
  .replace(/&#39;/g, "'").replace(/&amp;/g, '&');

let html = fs.readFileSync(FILE, 'utf8');
const before = Buffer.byteLength(html);

// ── 0. 멱등성 가드 ──────────────────────────────────────────────────
// 이미 후처리된 index.html 에 이 스크립트를 한 번 더 돌리면 코드 블록이 조용히 망가진다.
// 아래 2단계는 <pre><code> 안을 "아직 강조 안 된 코드"로 가정하는데, 재실행 시엔
// 이미 들어간 <span class="hljs-…"> 마크업을 코드 텍스트로 보고 다시 강조한다.
// 그 결과 태그가 이스케이프돼(&lt;span…) 본문에 그대로 노출된다. 현재 52개 중 32개가 해당.
// (mermaid·hljs CSS·#cv-sizes 단계는 재실행에 안전하다 — 이 가드는 코드 블록 때문에 있다.)
// 정상 파이프라인은 항상 이 한 쌍이다:  python3 build_course.py && node tools/prerender.mjs
const MARKERS = [
  ['<style id="hljs-theme-css">', 'hljs 테마 CSS 인라인'],
  ['<figure class="mmd"', 'mermaid 인라인 SVG'],
];
const found = MARKERS.filter(([m]) => html.includes(m)).map(([, label]) => label);
if (found.length) {
  console.error(`index.html 은 이미 후처리된 상태입니다 (${found.join(', ')}).`);
  console.error('다시 돌리면 이미 강조된 코드 블록이 조용히 망가집니다. 빌드 출력에서 시작하세요:\n');
  console.error('  python3 build_course.py && node tools/prerender.mjs\n');
  process.exit(1);
}

// ── 1. mermaid 원본 수집 ────────────────────────────────────────────
const blocks = [...html.matchAll(/<pre class="mermaid">([\s\S]*?)<\/pre>/g)];
if (!blocks.length) {
  // 위 가드를 통과했으니 여기는 "빌드가 도표를 안 냈다"는 뜻이다.
  console.error('빌드 출력에 mermaid 블록이 없습니다 — build_course.py 를 확인하세요.');
  process.exit(1);
}
const sources = blocks.map(m => decode(m[1]).trim());
console.log(`mermaid 블록 ${sources.length}개`);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 900, height: 800 } });
await page.setContent('<!doctype html><html><body style="margin:0"><div id="host"></div></body></html>');

// 두 테마로 각각 렌더
const svgs = { dark: [], light: [] };
for (const theme of ['dark', 'light']) {
  const out = await page.evaluate(async ({ src, url, theme, font }) => {
    const mermaid = (await import(url)).default;
    mermaid.initialize({
      startOnLoad: false, theme: theme === 'dark' ? 'dark' : 'default', securityLevel: 'loose',
      fontFamily: font,
      flowchart: { htmlLabels: true, useMaxWidth: true, padding: 14 },
      themeVariables: { fontFamily: font, fontSize: '15px' },
    });
    const res = [];
    for (let i = 0; i < src.length; i++) {
      const { svg } = await mermaid.render(`mmd-${theme}-${i}`, src[i]);
      res.push(svg);
    }
    return res;
  }, { src: sources, url: MERMAID, theme, font: FONT });
  svgs[theme] = out;
  console.log(`  ${theme} 테마 렌더 완료 (${out.length}개)`);
}

// ── 2. 코드 하이라이트 ──────────────────────────────────────────────
const codeBlocks = [...html.matchAll(/<pre><code([^>]*)>([\s\S]*?)<\/code><\/pre>/g)];
console.log(`코드 블록 ${codeBlocks.length}개`);
const highlighted = await page.evaluate(async ({ url, items }) => {
  await new Promise((ok, err) => {
    const s = document.createElement('script'); s.src = url; s.onload = ok; s.onerror = err;
    document.head.appendChild(s);
  });
  return items.map(({ lang, code }) => {
    const el = document.createElement('div');
    el.textContent = code;                       // 엔티티 디코드 겸 이스케이프
    const text = el.textContent;
    try {
      const r = lang && hljs.getLanguage(lang) ? hljs.highlight(text, { language: lang })
                                               : hljs.highlightAuto(text);
      return r.value;
    } catch (_) { return el.innerHTML; }
  });
}, {
  url: HLJS,
  items: codeBlocks.map(m => ({
    lang: (m[1].match(/language-([\w-]+)/) || [])[1] || '',
    code: decode(m[2]),
  })),
});

// hljs 테마 CSS 두 벌을 받아 [data-theme] 로 스코프
const css = {};
for (const [k, url] of Object.entries(HL_CSS)) {
  css[k] = await (await fetch(url)).text();
}
const scope = (text, sel) => text
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/(^|})\s*([^{}@]+)\{/g, (_m, brace, sels) =>
    `${brace}${sels.split(',').map(s => `${sel} ${s.trim()}`).join(',')}{`);
const hlCss = scope(css.dark, ':root[data-theme="dark"]') + '\n' + scope(css.light, ':root[data-theme="light"]');

// ── 3. HTML 치환 ────────────────────────────────────────────────────
let ci = 0;
html = html.replace(/<pre><code([^>]*)>([\s\S]*?)<\/code><\/pre>/g,
  (_m, attrs) => `<pre><code${attrs}>${highlighted[ci++]}</code></pre>`);

// mermaid 원본에서 사람이 읽을 만한 대체 텍스트를 만든다.
// (노드 라벨을 순서대로 이어 붙임 — 스크린리더가 도표를 완전히 건너뛰지 않도록)
function altText(src) {
  const kind = /^\s*sequenceDiagram/.test(src) ? '시퀀스 다이어그램'
    : /^\s*(flowchart|graph)/.test(src) ? '흐름도'
    : /^\s*stateDiagram/.test(src) ? '상태 다이어그램'
    : /^\s*(mindmap|timeline)/.test(src) ? '개념도' : '다이어그램';
  const grab = (re, i = 1) => [...src.matchAll(re)].map(m => m[i]);
  const raw = [
    // 노드 라벨 — A[텍스트] · A(텍스트) · A{텍스트} · A[[텍스트]] · A(("텍스트"))
    ...grab(/\b[\w-]+\s*(?:\[\[|\(\(|\[\(|\[|\(|\{\{|\{|>)\s*"?([^"\]\)\}|\n]{2,60}?)"?\s*(?:\]\]|\)\)|\)\]|\]|\)|\}\}|\})/g),
    // 화살표 라벨 — -->|텍스트|
    ...grab(/\|\s*([^|\n]{2,40}?)\s*\|/g),
    // 시퀀스 다이어그램 — participant X as 이름 / A->>B: 메시지
    ...grab(/^\s*(?:participant|actor)\s+\S+\s+as\s+(.+)$/gm),
    ...grab(/^\s*\S+\s*-{1,2}>>?\s*\S+\s*:\s*(.+)$/gm),
  ];
  const labels = raw
    .map(s => s.replace(/<br\s*\/?>/gi, ' ').replace(/["`]/g, '').replace(/\s+/g, ' ')
      .replace(/^[\s|(\[]+|[\s|(\[]+$/g, '').trim())
    .filter(s => s.length >= 2 && !/^[-|>=.:\[\](){}]+$/.test(s) && !/^[A-Za-z]$/.test(s));
  const uniq = [...new Set(labels)].slice(0, 14);
  return uniq.length ? `${kind}: ${uniq.join(', ')}` : kind;
}

let mi = 0;
html = html.replace(/<pre class="mermaid">([\s\S]*?)<\/pre>/g, () => {
  const i = mi++;
  const alt = altText(sources[i]).replace(/"/g, '&quot;').replace(/</g, '&lt;');
  const strip = s => s.replace(/^<svg /, '<svg aria-hidden="true" focusable="false" ');
  return `<figure class="mmd" role="img" aria-label="${alt}">`
    + `<div class="mmd-dark">${strip(svgs.dark[i])}</div>`
    + `<div class="mmd-light">${strip(svgs.light[i])}</div>`
    + `</figure>`;
});

// hljs 테마 <link> → 인라인 <style>
html = html.replace(
  /<link rel="stylesheet" href="https:\/\/cdn\.jsdelivr\.net\/gh\/highlightjs[^>]*>/,
  `<style id="hljs-theme-css">\n${hlCss}\n</style>`);
// hljs 스크립트 제거
html = html.replace(/<script src="https:\/\/cdn\.jsdelivr\.net\/gh\/highlightjs[^"]*"[^>]*><\/script>\n?/, '');
// preconnect 제거
html = html.replace(/<link rel="preconnect" href="https:\/\/cdn\.jsdelivr\.net">\n?/, '');

// ── 4. 챕터별 실측 높이 → contain-intrinsic-size ────────────────────
// .chapter 는 content-visibility:auto 라 뷰포트 밖에선 "추정 높이"만 차지한다.
// 추정이 실제와 크게 다르면 스크롤바 길이가 틀리고, navTo 의 smooth scroll 이
// 이동 중 렌더되는 챕터들 때문에 목표를 빗나간다. 그래서 빌드 시점에 실제 높이를
// 재서 챕터별로 박아 둔다. 콘텐츠가 바뀌면 다음 빌드에서 자동으로 갱신된다.
html = html.replace(/<style id="cv-sizes">[\s\S]*?<\/style>\n?/, '');   // 재실행 대비

const TMP = path.join(ROOT, '.cv-measure.html');
fs.writeFileSync(TMP, html);

const BREAKPOINT = 900;          // build_course.py 의 @media(max-width:900px) 와 맞춰야 한다
const measure = async (width) => {
  const p = await browser.newPage({ viewport: { width, height: 900 } });
  await p.goto('file://' + TMP, { waitUntil: 'load' });
  // 건너뛴 챕터는 추정 높이를 보고하므로 재는 동안엔 전부 펼치되,
  // content-visibility:auto 가 걸어 두는 containment 는 그대로 유지해야 한다.
  // containment 를 빼고 재면 마진 상쇄가 살아나 챕터당 수 px 씩 낮게 나오고,
  // 그 오차가 이동 경로의 챕터 수만큼 누적된다.
  await p.addStyleTag({ content:
    '.chapter{content-visibility:visible !important;contain:layout style paint !important}' });
  await p.evaluate(() => document.fonts.ready);
  // contain-intrinsic-size 는 "콘텐츠 박스" 크기다. 보더 박스 높이를 그대로 넣으면
  // 챕터마다 padding-top(40px)+border(1px)만큼 부풀어, 이동 중 렌더되는 챕터 수에
  // 비례해 오차가 쌓이고 smooth scroll 이 목표를 지나쳐 버린다.
  const out = await p.evaluate(() => Object.fromEntries(
    [...document.querySelectorAll('.chapter[id]')].map(c => {
      const s = getComputedStyle(c);
      const pad = ['paddingTop', 'paddingBottom', 'borderTopWidth', 'borderBottomWidth']
        .reduce((a, k) => a + parseFloat(s[k] || 0), 0);
      return [c.id, Math.round(c.getBoundingClientRect().height - pad)];
    })));
  await p.close();
  return out;
};

const wide = await measure(1280);
const narrow = await measure(390);
await browser.close();
fs.unlinkSync(TMP);

const rule = (m) => Object.entries(m)
  .map(([id, h]) => `#${id}{contain-intrinsic-size:auto ${h}px}`).join('\n');
const cvCss = `<style id="cv-sizes">\n@media screen{\n${rule(wide)}\n`
  + `@media(max-width:${BREAKPOINT}px){\n${rule(narrow)}\n}\n}\n</style>`;

if (/<\/head>/.test(html)) {
  html = html.replace('</head>', cvCss + '\n</head>');
  console.log(`\n챕터 ${Object.keys(wide).length}개 실측 높이 주입 (#cv-sizes)`);
} else {
  console.log('\n</head> 를 찾지 못해 #cv-sizes 를 넣지 못했습니다 — 폴백 5000px 로 동작합니다.');
}

fs.writeFileSync(FILE, html);

const after = Buffer.byteLength(html);
const left = (html.match(/cdn\.jsdelivr\.net/g) || []).length;
console.log(`\nindex.html ${(before / 1024).toFixed(0)}KB → ${(after / 1024).toFixed(0)}KB`);
console.log(`남은 jsdelivr 참조: ${left}건 ${left === 0 ? '✓' : '(빌드 시점 전용 코드일 수 있음 — 확인 필요)'}`);
