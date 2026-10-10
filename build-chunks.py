#!/usr/bin/env python3
"""把各 article.html 按段落切块，生成 chunks.json 供问答 Agent 检索。
每次文章更新后重新跑一遍。
用法：python3 build-chunks.py
"""
import re, json, glob, os

ROOT = os.path.dirname(os.path.abspath(__file__))
DRAFTS = {'rpc', 'concurrent-hashmap', 'io-models', 'kubernetes', 'load-balancing'}

def clean(html):
    html = re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S)
    html = re.sub(r'<[^>]+>', '\n', html)
    html = re.sub(r'[ \t]+', ' ', html)
    return html

chunks = []
for p in sorted(glob.glob(os.path.join(ROOT, '*/article.html'))):
    topic = os.path.basename(os.path.dirname(p))
    if topic in DRAFTS:
        continue
    h = open(p, encoding='utf-8').read()
    title = re.search(r'<h1>(.*?)</h1>', h, re.S)
    title = clean(title.group(1)).strip() if title else topic
    body = re.search(r'<article>(.*?)</article>', h, re.S)
    if not body:
        continue
    text = clean(body.group(1))
    # 按空行/标题切段，过短的合并
    paras, buf = [], ""
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            if buf: paras.append(buf); buf = ""
            continue
        if len(buf) + len(line) > 600:
            paras.append(buf); buf = line
        else:
            buf = (buf + " " + line).strip()
    if buf: paras.append(buf)
    for para in paras:
        if len(para) < 40:
            continue
        chunks.append({"topic": topic, "title": title, "text": para[:800]})

out = os.path.join(ROOT, 'chunks.json')
json.dump(chunks, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f"{len(chunks)} 个块，{os.path.getsize(out)//1024} KB")
