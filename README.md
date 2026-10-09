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

## 预览

在线播放：https://mbwjs.github.io/science-explainer-videos/（需仓库开启 GitHub Pages）

首页按「计算机 · AI」「心理学 · 人生」分类，只列横屏版；竖屏版文件仍保留在 `happiness/vertical.html`。新增视频时在 `index.html` 的 `VIDEOS` 数组里加一行即可。

也可以用浏览器直接打开任意 HTML 文件。点击画面或按空格键暂停，底部进度条可以拖动。

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
