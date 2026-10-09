# 科普动画视频

用代码做的科普短片：每部片是一个独立的 HTML 文件，用 Canvas 逐帧绘制，可以直接在浏览器播放，也可以渲染成 MP4。

## 作品

| 主题 | 文件 | 画幅 | 时长 |
|---|---|---|---|
| 幸福的科学 | `happiness/vertical.html` | 竖屏 1080×1920（抖音） | 72s |
| 幸福的科学 | `happiness/landscape.html` | 横屏 1920×1080（B 站） | 72s |
| 人生的意义 | `meaning-of-life/landscape.html` | 横屏 1920×1080 | 72s |
| 什么是 LLM | `llm/landscape.html` | 横屏 1920×1080 | 72s |
| 从零做一个 Claude Code | `claude-code/landscape.html` | 横屏 1920×1080 | 84s |
| JVM 是什么 | `jvm/landscape.html` | 横屏 1920×1080 | 72s |
| RAG 是什么 | `rag/landscape.html` | 横屏 1920×1080 | 72s |
| 线程池是什么 | `thread-pool/landscape.html` | 横屏 1920×1080 | 80s |
| 积极心理学 | `positive-psychology/landscape.html` | 横屏 1920×1080 | 72s |
| Opus 5.5 是怎么做出视频的 | `opus-video/landscape.html` | 横屏 1920×1080 | 76s |
| MySQL 的 MVCC | `mysql-mvcc/landscape.html` | 横屏 1920×1080 | 80s |
| 按下回车后发生了什么 | `http-request/landscape.html` | 横屏 1920×1080 | 80s |
| TCP 三次握手 | `tcp-handshake/landscape.html` | 横屏 1920×1080 | 80s |
| 数据库索引：为什么是 B+ 树 | `bplus-tree/landscape.html` | 横屏 1920×1080 | 80s |
| 事务与 ACID | `transaction-acid/landscape.html` | 横屏 1920×1080 | 80s |
| Redis 缓存 | `redis-cache/landscape.html` | 横屏 1920×1080 | 80s |

### 幸福的科学
钩子 → 享乐适应（快乐曲线 + 跑步机）→ 哈佛成人发展研究（关系网络）→ 心流（挑战 × 技能坐标图）→ 今晚就能做的 3 件事 → 收尾

### 人生的意义
钩子 → 弗兰克尔与集中营里的「为什么」→ 意义的三个来源（创造 / 爱 / 面对）→ 快乐 ≠ 意义（鲍迈斯特的研究）→ 问自己 3 个问题 → 收尾

### 什么是 LLM
钩子（聊天气泡）→ 猜下一个词（概率条）→ 怎么学会的（文字流 + 神经网络 + 参数旋钮）→ 注意力机制（「它」指谁）→ 三个短板 → LLM 拆字收尾

### 从零做一个 Claude Code
终端演示 → 核心公式（大模型 + 工具 + 循环）→ Agent 循环图 → 十几行核心代码 → 工具定义（JSON Schema）→ 从能用到好用的 4 个细节 → 收尾

### JVM 是什么
一份代码到处运行 → 源码 → 字节码 → 机器码 → 内存区域（栈 / 堆 / 方法区）→ 垃圾回收（可达性分析 + 分代）→ JIT 即时编译 → 收尾

### RAG 是什么
钩子（模型不知道公司规定）→ 开卷考试比喻 + RAG 拆字 → 切块与向量化入库 → 向量空间里的语义检索 → 拼提示词生成带出处的回答 → 收尾

### 线程池是什么
新建线程的代价 → 银行柜台比喻 → 任务进入线程池的四步流转 → ThreadPoolExecutor 的 7 个参数 → 4 种拒绝策略 → 生产环境三个忠告 → 收尾

### 积极心理学
心理学过去在研究「病」→ 从 -5 到 +5 → PERMA 五根支柱 → 6 大美德与 24 项品格优势 → 研究验证过的 3 个小练习 → 积极心理学 ≠ 强颜欢笑

### Opus 5.5 是怎么做出视频的
视频全是代码画的 → 和视频生成模型的区别 → 四步流水线（脚本、HTML 动画、逐帧截图、ffmpeg）→ 画面 = 时间的函数 draw(t) → 写、看、改的自我检查循环 → 适合与不适合

### MySQL 的 MVCC
加锁导致读写互等 → 一行多版本 → 隐藏列与 undo 版本链 → ReadView 可见性规则与沿链查找 → RC 与 RR 的区别 → 快照读与当前读、长事务 → 收尾

### 按下回车后发生了什么
按下回车 → DNS 逐级查询 → TCP 三次握手与 TLS 握手 → HTTP 请求与响应、服务器内部 → 浏览器渲染流程 → 耗时分布与优化 → 收尾

### TCP 三次握手
不可靠的网络 → 三次握手与序列号 → 为什么必须三次（拒绝过期 SYN）→ 四次挥手与 TIME_WAIT → 重传、滑动窗口、拥塞控制 → SYN 洪水与 SYN Cookie → 收尾

### 数据库索引：为什么是 B+ 树
全表扫描 → 为什么不用哈希表和二叉树 → B+ 树查找与容量估算 → 叶子链表与范围查询 → 聚簇索引、回表、覆盖索引 → 最左前缀与索引失效 → 收尾

### 事务与 ACID
转账崩溃 → ACID 总览 → 原子性与 undo log → 持久性与 redo log、WAL → 隔离级别 → 一致性 → 写代码时的 3 个提醒 → 收尾

### Redis 缓存
数据库扛不住 → Redis 为什么快 → 五种数据类型 → 旁路缓存的读写流程 → 穿透、击穿、雪崩 → 持久化与高可用 → 收尾

## 预览

在线播放：https://mbwjs.github.io/science-explainer-videos/（需仓库开启 GitHub Pages）

首页按「AI 与大模型」「计算机与后端」「心理学 · 人生」分类，只列横屏版；竖屏版文件仍保留在 `happiness/vertical.html`。新增视频时在 `index.html` 的 `VIDEOS` 数组里加一行即可。

也可以用浏览器直接打开任意 HTML 文件。点击画面或按空格键暂停，底部进度条可以拖动。

## 图文文章

每部视频的目录下都有一篇配套的详解文章：`article.md` 是源文件，`article.html` 是生成的网页，`img/` 里是从视频截取的配图。

```bash
# 从视频截取配图（秒数可写多个）
node tools/snap.mjs llm/landscape.html llm/img 6 11.5 45
# 把所有 article.md 编译成 article.html
python3 tools/build_articles.py
```

## 导出 MP4

需要 Node.js 18+ 和 ffmpeg。

```bash
npm install
npx playwright install chromium
node render.mjs happiness/landscape.html happiness-landscape.mp4
```

可选参数：`--fps 30`、`--start 秒`、`--end 秒`（只渲染某一段，方便调试）。

原理：加上 `?render=1` 打开页面后，脚本逐帧调用 `window.renderFrame(t)`，截取画布，再通过管道交给 ffmpeg 编码为 H.264。

## 后期建议

视频里没有配音。可以在剪映里用「文本朗读」给画面文字配音，再加一段背景音乐。
