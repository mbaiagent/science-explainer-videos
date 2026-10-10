// 批量生成各动画的封面缩略图
// 用法: node thumb.mjs <chapters.json> <输出目录>
import { chromium } from 'playwright';
import path from 'node:path';
import fs from 'node:fs';

const [jsonPath, outDir] = process.argv.slice(2);
const chapters = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage();
for (const ch of chapters) {
  const topic = ch.path.split('/')[0];
  const htmlPath = path.resolve('..', 'science-explainer-videos', ch.path);
  // 用仓库本地路径
  await page.goto('file://' + path.resolve(ch.path) + '?render=1');
  await page.waitForFunction(() => window.ready);
  const dur = ch.dur || (await page.evaluate(() => window.DURATION));
  await page.evaluate(t => window.renderFrame(t), dur * 0.25);
  await page.evaluate(() => { document.getElementById('bar').style.display = 'none'; });
  const stage = page.locator('#stage');
  await stage.screenshot({ path: path.join(outDir, topic + '.jpg'), type: 'jpeg', quality: 80 });
  console.log('ok', topic);
}
await browser.close();
console.log('done');
