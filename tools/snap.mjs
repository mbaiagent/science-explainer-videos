// 从视频 HTML 截取关键帧，生成文章配图（JPG，宽 1280）
// 用法: node tools/snap.mjs <视频html> <输出目录> <秒数...>
import { chromium } from 'playwright';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const [input, outDir, ...times] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('file://' + path.resolve(input) + '?render=1');
await page.waitForFunction(() => window.ready);
const { w, h } = await page.evaluate(() => { const c = document.getElementById('stage'); return { w: c.width, h: c.height }; });
await page.setViewportSize({ width: w, height: h });
for (const t of times) {
  await page.evaluate(t => window.renderFrame(t), +t);
  const png = path.join(outDir, `f-${t}.png`), jpg = path.join(outDir, `f-${t}.jpg`);
  await page.locator('#stage').screenshot({ path: png });
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', png, '-vf', 'scale=1280:-1', '-q:v', '4', jpg]);
  fs.unlinkSync(png);
  console.log(jpg);
}
await browser.close();
