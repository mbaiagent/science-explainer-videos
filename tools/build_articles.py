"""把每个视频目录下的 article.md 编译成 article.html。
article.md 开头是元信息（直到第一个空行）：
  title: 标题
  subtitle: 一句话简介
  tag: 分类标签
  color: #rrggbb
其后是 Markdown 正文，可直接写 HTML（如内联 SVG）。
图片 ![说明](img/x.jpg) 会变成带说明文字的 figure。
用法: python3 tools/build_articles.py [目录...]
"""
import sys, re, glob, os, html
import markdown

TPL = '''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · 拾星</title>
<meta name="description" content="{subtitle_attr}">
<link rel="icon" href="/assets/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="stylesheet" href="../assets/article.css">
<style>:root{{--acc:{color}}}</style>
</head>
<body>
<div class="wrap">
  <nav class="top"><a href="../index.html">← 拾星 · 全部内容</a>{watch}</nav>
  <header class="hero">
    <div class="tag">拾星 · {tag}</div>
    <h1>{title}</h1>
    <p>{subtitle}</p>
    <div class="meta">约 {minutes} 分钟读完{durtxt}</div>
  </header>
  {toc}
  <article>
{body}
  </article>
  <div class="foot"><a href="../index.html">← 拾星首页</a>{watch2}</div>
</div>
<script src="../assets/stats.js" data-kind="reads"></script>
</body>
</html>
'''

def build(d):
    src = os.path.join(d, 'article.md')
    raw = open(src, encoding='utf-8').read()
    head, body = raw.split('\n\n', 1)
    body = body.replace('[TOC]', '')
    meta = dict(l.split(': ', 1) for l in head.strip().splitlines())
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc', 'sane_lists', 'md_in_html'], extension_configs={'toc': {'toc_depth': '2'}})
    out = md.convert(body)
    out = re.sub(r'<p>\s*<img alt="([^"]*)" src="([^"]+)"\s*/?>\s*</p>',
                 lambda m: f'<figure><img src="{m.group(2)}" alt="{m.group(1)}" loading="lazy"><figcaption>{m.group(1)}</figcaption></figure>', out)
    text_len = len(re.sub(r'<[^>]+>|\s', '', out))
    vp = os.path.join(d, 'landscape.html'); has = os.path.exists(vp)
    vid = open(vp, encoding='utf-8').read() if has else ''
    m = re.search(r'DUR = (\d+)', vid); dur = int(m.group(1)) if m else 72
    toc = md.toc.replace('<div class="toc">', '<nav class="toc">').replace('</div>', '</nav>') if md.toc_tokens else ''
    page = TPL.format(title=html.escape(meta['title']), subtitle=html.escape(meta['subtitle']), subtitle_attr=html.escape(meta['subtitle'], quote=True),
                      tag=html.escape(meta.get('tag', '科普')), color=meta.get('color', '#ffb36b'), minutes=max(3, round(text_len/450)),
                      durtxt=(f' · 配套视频 {dur//60}:{dur%60:02d}' if has else ' · 图文'), watch=('<a class="watch" href="landscape.html">▶ 看视频</a>' if has else ''), watch2=('<a href="landscape.html">▶ 看配套视频</a>' if has else ''), toc=toc, body=out)
    open(os.path.join(d, 'article.html'), 'w', encoding='utf-8').write(page)
    print(f'{d}/article.html  {text_len} 字')

dirs = sys.argv[1:] or sorted(os.path.dirname(p) for p in glob.glob('*/article.md'))
for d in dirs: build(d)
