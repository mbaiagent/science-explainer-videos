// 把 HTML 动画逐帧渲染成 MP4
// 用法: node render.mjs <html文件> <输出.mp4> [--fps 30] [--start 0] [--end 时长]
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import path from 'node:path';

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? +args[i + 1] : d; };
const [input, output] = args.filter((a, i) => !a.startsWith('--') && !args[i - 1]?.startsWith('--'));
if (!input || !output) { console.error('用法: node render.mjs <html> <out.mp4> [--fps 30] [--start 0] [--end N]'); process.exit(1); }
const fps = opt('--fps', 30);

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('file://' + path.resolve(input) + '?render=1');
await page.waitForFunction(() => window.ready);
const { w, h, dur } = await page.evaluate(() => {
  const c = document.getElementById('stage'); return { w: c.width, h: c.height, dur: window.DURATION };
});
await page.setViewportSize({ width: w, height: h });
const start = opt('--start', 0), end = opt('--end', dur);
const frames = Math.round((end - start) * fps);

const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
  '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', output],
  { stdio: ['pipe', 'inherit', 'inherit'] });
const stage = page.locator('#stage');
for (let i = 0; i < frames; i++) {
  await page.evaluate(t => window.renderFrame(t), start + i / fps);
  const buf = await stage.screenshot({ type: 'png' });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (i % fps === 0) process.stdout.write(`\r${(i / fps).toFixed(0)}s / ${(frames / fps).toFixed(0)}s`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
console.log(`\n完成: ${output} (${w}×${h}, ${fps}fps, ${frames} 帧)`);
