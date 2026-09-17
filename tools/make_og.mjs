/**
 * 소셜 공유 카드(OG Image - 1200x630) 생성 스크립트
 *
 *   node tools/make_og.mjs
 *
 * Playwright 를 활용해 고해상도 다크 테마 기반의 og.png 를 생성합니다.
 */
import { chromium } from 'playwright';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { ensureChromeDeps } from './chromedeps.mjs';

ensureChromeDeps();

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'og.png');

const HTML = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1200px;
    height: 630px;
    background: #0e0f13;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    color: #e7e3da;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    position: relative;
  }
  .bg-glow {
    position: absolute;
    width: 700px;
    height: 700px;
    background: radial-gradient(circle, rgba(224, 122, 75, 0.16) 0%, rgba(201, 168, 106, 0.08) 45%, rgba(14, 15, 19, 0) 75%);
    top: -150px;
    right: -100px;
    pointer-events: none;
  }
  .card {
    width: 1120px;
    height: 550px;
    background: rgba(21, 23, 29, 0.92);
    border: 1.5px solid #2a2d38;
    border-radius: 20px;
    padding: 38px 46px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.5);
    position: relative;
    z-index: 1;
  }
  .top-bar {
    display: flex;
    align-items: center;
    gap: 9px;
  }
  .dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; }
  .dot.r { background: #e05f5f; }
  .dot.y { background: #e0b45f; }
  .dot.g { background: #5fe07a; }
  .top-tag {
    margin-left: 10px;
    font-family: monospace;
    font-size: 14px;
    color: #a7a396;
    letter-spacing: 0.5px;
  }
  .badge-top {
    margin-left: auto;
    background: rgba(224, 122, 75, 0.15);
    border: 1px solid rgba(224, 122, 75, 0.4);
    color: #e07a4b;
    font-size: 13px;
    font-weight: 700;
    padding: 5px 14px;
    border-radius: 20px;
    letter-spacing: 0.3px;
  }
  .hero {
    margin-top: 10px;
  }
  .title {
    font-size: 50px;
    font-weight: 850;
    letter-spacing: -0.8px;
    color: #ffffff;
    line-height: 1.15;
    margin-bottom: 12px;
  }
  .title span {
    color: #e07a4b;
  }
  .desc {
    font-size: 21px;
    color: #a7a396;
    line-height: 1.45;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin: 18px 0 12px;
  }
  .box {
    background: #1a1d24;
    border: 1px solid #2a2d38;
    border-radius: 12px;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .box-title {
    font-size: 15px;
    font-weight: 700;
    color: #e7e3da;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .box-sub {
    font-size: 12px;
    color: #7f7c72;
    line-height: 1.35;
  }
  .footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-top: 1px solid #2a2d38;
    padding-top: 16px;
    font-size: 14px;
    color: #7f7c72;
  }
  .footer b {
    color: #c9a86a;
    font-family: monospace;
    font-weight: 600;
  }
  .footer .url {
    color: #a7a396;
    font-family: monospace;
  }
</style>
</head>
<body>
  <div class="bg-glow"></div>
  <div class="card">
    <div class="top-bar">
      <span class="dot r"></span>
      <span class="dot y"></span>
      <span class="dot g"></span>
      <span class="top-tag">claude-code-tutorial-ko.vercel.app</span>
      <span class="badge-top">2026 최신 개정판 · 18 챕터</span>
    </div>

    <div class="hero">
      <h1 class="title">Claude Code <span>마스터 클래스</span></h1>
      <p class="desc">설치·권한·모델부터 서브에이전트·스킬·훅·루프 엔지니어링까지 한국어 실전 가이드</p>
    </div>

    <div class="grid">
      <div class="box">
        <div class="box-title">📚 18개 실무 챕터</div>
        <div class="box-sub">기초부터 대규모 에이전틱 오케스트레이션까지</div>
      </div>
      <div class="box">
        <div class="box-title">⚡ Fable 5.1 & Opus 5</div>
        <div class="box-sub">16대 공식 가이드 & 최신 모델 라인업 반영</div>
      </div>
      <div class="box">
        <div class="box-title">🛠️ 대화형 놀이터 6종</div>
        <div class="box-sub">터미널·진단기·계산기·검사기·튜너·권한 시뮬레이터</div>
      </div>
      <div class="box">
        <div class="box-title">🎓 확인 퀴즈 & 수료증</div>
        <div class="box-sub">챕터별 실전 문제풀이 및 맞춤형 수료증 PNG 발급</div>
      </div>
    </div>

    <div class="footer">
      <div>한국어 종합 실전 강의 · <b>제작: AI_Innovation_Studio</b></div>
      <div class="url">https://claude-code-tutorial-ko.vercel.app</div>
    </div>
  </div>
</body>
</html>`;

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await page.setContent(HTML, { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: OUT, type: 'png' });
await browser.close();
console.log(`✓ og.png 생성 완료 (1200x630): ${OUT}`);
