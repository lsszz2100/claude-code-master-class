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
 *
 * 결과: 런타임 외부 요청 0건. mermaid·hljs 는 이 스크립트가 도는 빌드 시점에만 받는다.
 * 이 단계를 건너뛰어도 사이트는 CDN 폴백으로 동작한다(느릴 뿐).
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

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

// ── 1. mermaid 원본 수집 ────────────────────────────────────────────
const blocks = [...html.matchAll(/<pre class="mermaid">([\s\S]*?)<\/pre>/g)];
if (!blocks.length) {
  console.log('미리 렌더할 mermaid 블록이 없습니다 (이미 처리됨).');
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

await browser.close();

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

fs.writeFileSync(FILE, html);

const after = Buffer.byteLength(html);
const left = (html.match(/cdn\.jsdelivr\.net/g) || []).length;
console.log(`\nindex.html ${(before / 1024).toFixed(0)}KB → ${(after / 1024).toFixed(0)}KB`);
console.log(`남은 jsdelivr 참조: ${left}건 ${left === 0 ? '✓' : '(빌드 시점 전용 코드일 수 있음 — 확인 필요)'}`);
