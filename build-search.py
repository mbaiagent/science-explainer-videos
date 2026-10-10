#!/usr/bin/env python3
"""从各主题 article.html 抽取全文，生成 search.json 供 search.html 做客户端全文检索。
每次仓库 pull 到新文章后重新跑一遍，再部署。
用法：python3 build-search.py
"""
import re, json, glob, os

ROOT = os.path.dirname(os.path.abspath(__file__))

def clean(html):
    html = re.sub(r'<script.*?</script>|<style.*?</style>', '', html, flags=re.S)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = re.sub(r'\s+', ' ', html)
    return html.strip()

docs = []
for p in sorted(glob.glob(os.path.join(ROOT, '*/article.html'))):
    topic = os.path.basename(os.path.dirname(p))
    h = open(p, encoding='utf-8').read()
    title = re.search(r'<h1>(.*?)</h1>', h, re.S)
    title = clean(title.group(1)) if title else topic
    desc = re.search(r'<meta name="description" content="([^"]*)"', h)
    desc = desc.group(1) if desc else ''
    body = re.search(r'<article>(.*?)</article>', h, re.S)
    text = clean(body.group(1)) if body else ''
    # 去掉尾部导航噪音
    text = re.sub(r'← 拾星首页.*$', '', text).strip()
    docs.append({'topic': topic, 'title': title, 'desc': desc, 'text': text})

out = os.path.join(ROOT, 'search.json')
json.dump(docs, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
total = sum(len(d['text']) for d in docs)
print(f'{len(docs)} 篇，{out}，正文共 {total} 字，{os.path.getsize(out)//1024} KB')
