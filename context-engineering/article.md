title: 上下文工程：决定 Agent 好坏的那块窗口
subtitle: 为什么只调提示词不够了，上下文里都装了什么，窗口为什么有限又昂贵（成本、延迟、中间遗忘），写入、选择、压缩、隔离四种策略，工具结果的裁剪，排列顺序与提示词缓存，长任务的压缩与进度文件，附一个带 token 预算的 Agent 循环
tag: AI 与大模型
color: #7dd3fc

## 一个常见的翻车现场

让一个编程 Agent 修一个线上 bug，任务描述里写清楚了一条约束：「不要修改对外的公共接口」。

前几步一切正常：它读日志、搜代码、定位到出错的函数。为了确认问题，它把一份几千行的日志整份读了进来，又打开了五六个文件，跑了两轮测试，每轮测试输出好几百行。到第 30 步左右，它终于改好了 bug，顺手把一个公共接口的参数也改了。

模型没有变笨，那条约束也一直「在」对话里。问题出在：第 30 步时，模型面对的是几万个 token 的输入，那条约束只是开头的一句话，前后夹着大量日志和测试输出。它被淹没了。

这类问题，换一个更好的提示词往往解决不了，因为提示词只是输入的一小部分。真正要管的，是**每一步送进模型的那一整块内容**：放什么、不放什么、放多少、按什么顺序放。这件事现在有一个专门的名字：**上下文工程**（Context Engineering）。

## 从提示词工程到上下文工程

### 模型每一步只看得到窗口里的东西

大模型本身是**无状态**的。它不会「记住」上一次调用发生了什么，每次调用都是把一段输入（上下文）交给它，它根据这段输入生成输出。所谓「多轮对话」，是应用程序每次把之前的对话重新拼进输入里。

Agent 也是这样工作的。本系列《Agent 设计模式》里讲过 Agent 的基本循环：

1. 把当前上下文发给模型；
2. 模型决定调用某个工具（或者给出最终回答）；
3. 程序执行工具，把结果**追加**到上下文里；
4. 回到第 1 步。

所以在第 N 步，模型对这个任务的全部认知，就是此刻上下文窗口里的内容。窗口里没有的，它不知道；窗口里有但被淹没的，它可能注意不到；窗口里有错误信息，它会当真。

有一个常见的类比：模型像 CPU，上下文窗口像内存。CPU 再快，内存里装的是错的数据、无关的数据，算出来的结果也不会好。操作系统要管理内存，Agent 系统就要管理上下文。

### 两者的区别

| | 提示词工程 | 上下文工程 |
|---|---|---|
| 关注对象 | 一段指令怎么写 | 每一步送给模型的全部内容 |
| 典型场景 | 单次调用：分类、抽取、写作 | 多轮运行的 Agent、长对话、长任务 |
| 主要问题 | 说清楚需求、给示例、定格式 | 放什么、放多少、怎么排、什么时候清理 |
| 时间维度 | 写一次，反复用 | 每一轮都要重新决定 |
| 涉及的东西 | 系统提示、少样本示例 | 系统提示、工具定义、历史、工具结果、检索文档、记忆、任务状态 |

提示词工程没有过时，它是上下文工程的一部分：系统提示依然要写好（见本系列《Prompt 工程与结构化输出》）。但对于 Agent 来说，系统提示可能只占上下文的百分之几，剩下的大部分内容是在运行过程中**动态长出来的**。上下文工程要管的，正是这部分。

## 上下文里都有什么

<figure>
<svg viewBox="0 0 440 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="上下文窗口的组成">
  <rect width="440" height="420" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif">
    <text x="220" y="30" fill="#7dd3fc" font-size="18" font-weight="800" text-anchor="middle">一次调用送进模型的内容</text>
    <g text-anchor="middle" font-size="14" font-weight="700">
      <rect x="20" y="50" width="220" height="36" rx="8" fill="rgba(125,211,252,.22)" stroke="#7dd3fc"/>
      <text x="130" y="73" fill="#f4ede4">系统提示</text>
      <rect x="20" y="90" width="220" height="36" rx="8" fill="rgba(125,211,252,.22)" stroke="#7dd3fc"/>
      <text x="130" y="113" fill="#f4ede4">工具定义</text>
      <rect x="20" y="130" width="220" height="32" rx="8" fill="rgba(134,239,172,.14)" stroke="#86efac"/>
      <text x="130" y="151" fill="#f4ede4">记忆 / 项目说明</text>
      <rect x="20" y="166" width="220" height="40" rx="8" fill="rgba(134,239,172,.14)" stroke="#86efac"/>
      <text x="130" y="191" fill="#f4ede4">检索到的文档</text>
      <rect x="20" y="210" width="220" height="56" rx="8" fill="rgba(255,211,138,.14)" stroke="#ffd38a"/>
      <text x="130" y="243" fill="#f4ede4">对话历史</text>
      <rect x="20" y="270" width="220" height="72" rx="8" fill="rgba(255,211,138,.14)" stroke="#ffd38a"/>
      <text x="130" y="311" fill="#f4ede4">工具调用与结果</text>
      <rect x="20" y="346" width="220" height="32" rx="8" fill="rgba(249,168,212,.16)" stroke="#f9a8d4"/>
      <text x="130" y="367" fill="#f4ede4">当前任务状态 / 新消息</text>
    </g>
    <g font-size="13">
      <line x1="252" y1="52" x2="252" y2="124" stroke="#7dd3fc" stroke-width="2"/>
      <text x="262" y="84" fill="#7dd3fc" font-weight="700">基本不变，放最前</text>
      <text x="262" y="104" fill="#9a93a8">可以命中提示词缓存</text>
      <line x1="252" y1="132" x2="252" y2="204" stroke="#86efac" stroke-width="2"/>
      <text x="262" y="162" fill="#86efac" font-weight="700">按需选择</text>
      <text x="262" y="182" fill="#9a93a8">不是越多越好</text>
      <line x1="252" y1="212" x2="252" y2="340" stroke="#ffd38a" stroke-width="2"/>
      <text x="262" y="270" fill="#ffd38a" font-weight="700">每一步都在变长</text>
      <text x="262" y="290" fill="#9a93a8">需要裁剪、压缩</text>
      <line x1="252" y1="348" x2="252" y2="376" stroke="#f9a8d4" stroke-width="2"/>
      <text x="262" y="367" fill="#f9a8d4" font-weight="700">每轮都不同</text>
      <text x="220" y="405" fill="#9a93a8" text-anchor="middle">模型输出 → 执行工具 → 结果追加进窗口 → 下一轮</text>
    </g>
  </g>
</svg>
<figcaption>Agent 每一步的输入，由七类内容拼成；后两类会随运行不断增长</figcaption>
</figure>

| 组成部分 | 内容 | 什么时候变 | 常见问题 |
|---|---|---|---|
| **系统提示** | 角色、规则、工作方式、输出要求 | 基本不变 | 写得太空泛，或者把所有可能用到的规则都塞进去 |
| **工具定义** | 每个工具的名字、描述、参数 JSON Schema | 基本不变 | 接了很多 MCP 服务器后，定义本身就占几万 token |
| **记忆 / 项目说明** | 用户偏好、项目约定（如 CLAUDE.md）、上次会话的结论 | 跨会话变化 | 选错了记忆，把无关信息带进来 |
| **检索到的文档** | RAG 召回的片段、搜索结果、读取的文件 | 按需 | 召回太多、相关度低，干扰判断 |
| **对话历史** | 用户和模型之前的每一轮消息 | 每轮增长 | 无限增长，早期的关键要求被淹没 |
| **工具调用与结果** | 模型发出的调用参数、工具返回的内容 | 每步增长 | 一条结果就有几千行；已经用过的结果一直留着 |
| **当前任务状态** | 目标、计划、待办清单、已完成的步骤 | 每步变化 | 根本没有显式记录，只能靠模型从历史里「回忆」 |

前两类几乎不变，中间两类是「选」进来的，后三类是运行中「长」出来的。上下文工程的大部分工作，都围绕着后几类展开。

这里有一个容易忽略的点：**工具定义也是上下文**。模型要知道有哪些工具、怎么调用，就必须在每次请求里看到它们的描述。Anthropic 在一篇介绍工具搜索的工程博客里举过一个例子：接入 GitHub、Slack、Sentry、Grafana、Splunk 五个 MCP 服务器，一共 58 个工具，对话还没开始，工具定义就已经占了约 55K token。

## 为什么上下文有限且昂贵

<figure>
<svg viewBox="0 0 440 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="中间遗忘的U形曲线示意">
  <rect width="440" height="300" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif">
    <text x="220" y="30" fill="#7dd3fc" font-size="18" font-weight="800" text-anchor="middle">中间遗忘：U 形曲线（示意）</text>
    <line x1="60" y1="60" x2="60" y2="230" stroke="#9a93a8" stroke-width="1.5"/>
    <line x1="60" y1="230" x2="410" y2="230" stroke="#9a93a8" stroke-width="1.5"/>
    <text x="48" y="145" fill="#9a93a8" font-size="13" text-anchor="middle" transform="rotate(-90 48 145)">答对率</text>
    <path d="M80,78 C140,150 170,190 235,192 C300,194 340,150 395,96" fill="none" stroke="#7dd3fc" stroke-width="3"/>
    <circle cx="80" cy="78" r="5" fill="#7dd3fc"/>
    <circle cx="235" cy="192" r="5" fill="#7dd3fc"/>
    <circle cx="395" cy="96" r="5" fill="#7dd3fc"/>
    <line x1="60" y1="168" x2="410" y2="168" stroke="#ffd38a" stroke-width="1.5" stroke-dasharray="6 5"/>
    <text x="416" y="194" fill="#ffd38a" font-size="13" text-anchor="end">不给文档时的水平</text>
    <text x="235" y="214" fill="#f4ede4" font-size="13" text-anchor="middle">放在中间：最差</text>
    <g fill="#9a93a8" font-size="13" text-anchor="middle">
      <text x="80" y="252">开头</text>
      <text x="235" y="252">中间</text>
      <text x="395" y="252">结尾</text>
      <text x="235" y="282">相关信息在输入中的位置</text>
    </g>
  </g>
</svg>
<figcaption>示意图：相关信息放在长输入的开头或结尾时答得最好，放在中间时最差，甚至可能不如不给文档</figcaption>
</figure>

现在主流模型的上下文窗口动辄几十万甚至上百万 token，看起来足够大。但「能装下」和「该装进去」是两回事。上下文至少有四种代价。

### 1. 硬上限

窗口满了就是满了。超出上限的请求会直接报错，或者被框架截掉最早的内容。对于跑几十上百步的 Agent 来说，不做任何管理，迟早会撞上限。Anthropic 在介绍多 Agent 研究系统时也提到，上下文超过 200,000 token 就会被截断，所以主 Agent 要先把计划存到外部的记忆里。

### 2. 成本：每一步都要为整段上下文付费

模型按 token 计费，而 Agent 的每一步都要把**完整的上下文**重新发一遍。假设每步平均新增 2,000 token，跑 50 步：

- 最后一步的输入约 100K token；
- 50 步累计的输入是 2K + 4K + … + 100K ≈ **255 万 token**。

累计输入随步数近似**平方增长**。Agent 的输出通常很短（一个工具调用就几十个 token），输入却越来越长。Manus 团队在分享上下文工程经验时提到，他们的 Agent 平均输入和输出的 token 比约为 100:1。对 Agent 来说，钱主要花在「读」上，而不是「写」上。

### 3. 延迟

模型处理输入（预填充，prefill）需要时间，输入越长，生成第一个 token 之前等得越久。每一步都慢一点，几十步累积起来，用户就能明显感觉到。提示词缓存可以大幅缓解这一点，后面专门讲。

### 4. 注意力被稀释：越长越不准

这是最反直觉的一点：**上下文越长，模型对其中信息的利用越差**，即使完全没超出窗口上限。

- **原理上**：Transformer 的自注意力让每个 token 都和其他所有 token 计算关系，n 个 token 就有 n² 对关系（见本系列《Transformer 详解》）。Anthropic 在《Effective context engineering for AI agents》中把这比作一份「注意力预算」：每多一个 token，都在消耗这份预算；
- **中间遗忘**（Lost in the Middle）：Liu et al. 在 2023 年发表的论文（TACL 2024）用多文档问答和键值检索两类任务测试了多个模型，发现相关信息位于输入的**开头或结尾**时效果最好，位于**中间**时明显下降，呈 U 形曲线。在 20 篇和 30 篇文档的设置下，GPT-3.5-Turbo 在相关文档位于中间时的准确率，甚至低于完全不给文档、只靠自身知识作答时的 56.1%；
- **上下文腐烂**（Context Rot）：向量数据库公司 Chroma 在 2025 年发布的技术报告测试了 18 个模型，发现即使是很简单的任务，随着输入变长，表现也会下降；与答案相似但不正确的「干扰项」越多，下降越明显。在 LongMemEval 上，只给相关片段（约 100 token 的聚焦输入）比给出约 12 万 token 的完整对话历史，模型的表现明显更好。

需要说明的是，「中间遗忘」的 U 形规律并不总能复现：Chroma 的报告就没有观察到稳定的位置效应，新模型的长上下文能力也在持续改进。但「无关内容越多，模型越容易出错」这个大方向，在各家的研究和工程经验里是一致的。

**结论：窗口大小是上限，不是目标。** 上下文工程的目标，可以用 Anthropic 那篇文章里的一句话概括：找到**最小的一组高信号 token**，让模型最大概率地做出想要的行为。

## 四种核心策略：写入、选择、压缩、隔离

<figure>
<svg viewBox="0 0 440 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="上下文工程的四种策略">
  <rect width="440" height="360" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="30" fill="#7dd3fc" font-size="18" font-weight="800">管理上下文的四种策略</text>
    <rect x="14" y="48" width="200" height="140" rx="14" fill="rgba(125,211,252,.10)" stroke="#7dd3fc"/>
    <text x="114" y="82" fill="#7dd3fc" font-size="20" font-weight="800">写入</text>
    <text x="114" y="110" fill="#f4ede4" font-size="14" font-weight="700">把信息存到窗口外</text>
    <text x="114" y="138" fill="#9a93a8" font-size="13">笔记、待办文件</text>
    <text x="114" y="160" fill="#9a93a8" font-size="13">长期记忆</text>
    <rect x="226" y="48" width="200" height="140" rx="14" fill="rgba(134,239,172,.10)" stroke="#86efac"/>
    <text x="326" y="82" fill="#86efac" font-size="20" font-weight="800">选择</text>
    <text x="326" y="110" fill="#f4ede4" font-size="14" font-weight="700">需要时才拉进来</text>
    <text x="326" y="138" fill="#9a93a8" font-size="13">按需检索、grep</text>
    <text x="326" y="160" fill="#9a93a8" font-size="13">按需加载工具和技能</text>
    <rect x="14" y="204" width="200" height="140" rx="14" fill="rgba(255,211,138,.10)" stroke="#ffd38a"/>
    <text x="114" y="238" fill="#ffd38a" font-size="20" font-weight="800">压缩</text>
    <text x="114" y="266" fill="#f4ede4" font-size="14" font-weight="700">只留必要的 token</text>
    <text x="114" y="294" fill="#9a93a8" font-size="13">清理旧的工具结果</text>
    <text x="114" y="316" fill="#9a93a8" font-size="13">摘要、截断</text>
    <rect x="226" y="204" width="200" height="140" rx="14" fill="rgba(249,168,212,.10)" stroke="#f9a8d4"/>
    <text x="326" y="238" fill="#f9a8d4" font-size="20" font-weight="800">隔离</text>
    <text x="326" y="266" fill="#f4ede4" font-size="14" font-weight="700">拆到不同的窗口里</text>
    <text x="326" y="294" fill="#9a93a8" font-size="13">子 Agent 独立上下文</text>
    <text x="326" y="316" fill="#9a93a8" font-size="13">只回传精简结果</text>
  </g>
</svg>
<figcaption>写入和选择决定什么进出窗口，压缩控制窗口里的体积，隔离把工作拆到多个窗口</figcaption>
</figure>

LangChain 在 2025 年的一篇博客里把常见做法归纳成四类：**写入**（Write）、**选择**（Select）、**压缩**（Compress）、**隔离**（Isolate）。这个分法很好记，下面逐个展开。

### 写入：把信息放到窗口外面

窗口是「工作台」，不是「仓库」。不需要一直摆在台面上的东西，应该存到外面，需要时再拿回来。

- **笔记 / 草稿本**：让 Agent 在执行过程中把发现、决定、未解决的问题写进文件，比如 `NOTES.md`。上下文被压缩或者重开新会话后，读一下笔记就能接上；
- **待办清单**：把计划写成 `todo.md` 一类的文件，每完成一步就更新。Manus 团队分享过一个做法：一个典型任务要调用约 50 次工具，他们让 Agent 反复改写待办清单，相当于把全局目标「复述」到上下文的末尾，放在模型最近的注意力范围内，减少跑偏；
- **长期记忆**：跨会话保留用户偏好、项目约定、过去的结论。Anthropic 提供的 memory tool 就是一种文件式的记忆：模型可以在一个专门的目录里创建、读取、修改文件，存储由开发者自己实现（详见本系列《Agent 的记忆》）。

写入还有一个好处：**让压缩变得可恢复**。比如网页内容可以从上下文里删掉，只要保留 URL；文件内容可以删掉，只要保留路径。需要时再读一次即可，信息没有真正丢失。

### 选择：只在需要时拉进来

和「写入」相对，「选择」决定什么时候、把哪些东西放进窗口。

- **按需检索，而不是预先全塞**：传统 RAG 是在调用模型之前，把检索到的片段一次性放进去。Agent 可以换一种方式：只在上下文里保留轻量的「线索」（文件路径、查询语句、链接），让模型自己决定什么时候用工具去读。Anthropic 把它称为「即时」（just-in-time）检索。Claude Code 用的是混合方式：项目说明文件 CLAUDE.md 一开始就加载，具体代码则让模型用 glob、grep 等工具按需查找；
- **按需加载工具**：工具多了以后，不要把所有工具的定义都放进去。Anthropic 的工具搜索（Tool Search Tool）允许把工具标记为延迟加载（`defer_loading`），模型先搜索、再加载需要的那几个。按其官方博客的数据，在 50 多个 MCP 工具的场景下，这样做能把开始工作前占用的 token 减少约 85%；
- **按需加载技能**：Agent Skills 采用「渐进式披露」：启动时只把每个技能的名字和一句描述放进系统提示，判断某个技能有用时才读取完整的 `SKILL.md`，更细的参考文件则在需要时再读（详见本系列《Skills 技能包》）；
- **选择记忆要谨慎**：记忆选错了比没有记忆更糟。LangChain 那篇博客里举过一个例子：用户让 ChatGPT 生成一张图片，结果它自作主张地把记忆里的用户所在地加进了图片。

「选择」的难点在于**召回质量**。选少了，模型缺信息，只能猜；选多了，又回到注意力被稀释的问题。实践中通常先用便宜的方式（关键词、元数据过滤）粗选，再用向量相似度或重排模型精选（见本系列《RAG 是什么》）。

### 压缩：只保留完成任务需要的 token

窗口里已经有的内容，用不上的就该瘦身。从轻到重有几档：

| 做法 | 怎么做 | 信息损失 | 适合 |
|---|---|---|---|
| **清理旧工具结果** | 很早之前的工具结果换成一句占位符，保留「调用过这个工具」的记录 | 低，需要时可以重新调用 | 读文件、搜索、API 返回这类可重新获取的内容 |
| **截断** | 超长内容只保留开头、结尾和关键行 | 中 | 日志、测试输出、长列表 |
| **裁剪历史** | 丢掉最早的若干轮对话 | 高，可能丢掉关键约束 | 闲聊类场景；Agent 慎用 |
| **摘要（compaction）** | 让模型把旧的对话总结成一段文字，替换原文 | 中到高，取决于摘要质量 | 长任务、长对话 |

Anthropic 在文章里把「清理旧工具结果」称为最安全、最轻量的一种压缩：一个工具调用发生在很久之前，模型通常不需要再看到它的原始输出了。他们的 API 也提供了对应的能力（context editing），可以在上下文接近阈值时自动清理旧的工具结果。官方公布的内部测试中，在一个 100 轮的网页搜索评测里，这一功能让 token 消耗减少了 84%。

摘要是最常用、也最需要小心的一种。下面讲长任务时再详细说。

### 隔离：把工作拆到不同的窗口

<figure>
<svg viewBox="0 0 440 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="子 Agent 上下文隔离">
  <rect width="440" height="340" fill="#0f0e1c"/>
  <defs><marker id="ce-ar1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#7dd3fc"/></marker>
  <marker id="ce-ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#86efac"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="30" fill="#7dd3fc" font-size="18" font-weight="800">子 Agent：各用各的窗口</text>
    <rect x="90" y="48" width="260" height="62" rx="12" fill="rgba(125,211,252,.16)" stroke="#7dd3fc"/>
    <text x="220" y="74" fill="#f4ede4" font-size="15" font-weight="800">主 Agent</text>
    <text x="220" y="96" fill="#9a93a8" font-size="13">上下文：目标、计划、各子任务结论</text>
    <line x1="150" y1="112" x2="84" y2="178" stroke="#7dd3fc" stroke-width="2" marker-end="url(#ce-ar1)"/>
    <line x1="210" y1="112" x2="210" y2="178" stroke="#7dd3fc" stroke-width="2" marker-end="url(#ce-ar1)"/>
    <line x1="280" y1="112" x2="346" y2="178" stroke="#7dd3fc" stroke-width="2" marker-end="url(#ce-ar1)"/>
    <line x1="104" y1="180" x2="170" y2="114" stroke="#86efac" stroke-width="2" stroke-dasharray="5 4" marker-end="url(#ce-ar2)"/>
    <line x1="230" y1="180" x2="230" y2="114" stroke="#86efac" stroke-width="2" stroke-dasharray="5 4" marker-end="url(#ce-ar2)"/>
    <line x1="366" y1="180" x2="300" y2="114" stroke="#86efac" stroke-width="2" stroke-dasharray="5 4" marker-end="url(#ce-ar2)"/>
    <g font-size="13">
      <rect x="14" y="182" width="130" height="76" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="79" y="208" fill="#f4ede4" font-weight="700">子 Agent A</text>
      <text x="79" y="230" fill="#9a93a8">大量搜索与阅读</text>
      <text x="79" y="248" fill="#9a93a8">独立上下文</text>
      <rect x="155" y="182" width="130" height="76" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="220" y="208" fill="#f4ede4" font-weight="700">子 Agent B</text>
      <text x="220" y="230" fill="#9a93a8">大量搜索与阅读</text>
      <text x="220" y="248" fill="#9a93a8">独立上下文</text>
      <rect x="296" y="182" width="130" height="76" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="361" y="208" fill="#f4ede4" font-weight="700">子 Agent C</text>
      <text x="361" y="230" fill="#9a93a8">大量搜索与阅读</text>
      <text x="361" y="248" fill="#9a93a8">独立上下文</text>
      <line x1="40" y1="286" x2="62" y2="286" stroke="#7dd3fc" stroke-width="2"/>
      <text x="68" y="291" fill="#9a93a8" text-anchor="start">派发子任务</text>
      <line x1="210" y1="286" x2="232" y2="286" stroke="#86efac" stroke-width="2" stroke-dasharray="5 4"/>
      <text x="238" y="291" fill="#9a93a8" text-anchor="start">只回传精简结论</text>
      <text x="220" y="322" fill="#f4ede4">探索过程留在子 Agent 里，主窗口保持干净</text>
    </g>
  </g>
</svg>
<figcaption>每个子 Agent 在自己的窗口里探索，只把压缩后的结论交给主 Agent</figcaption>
</figure>

一个窗口装不下、或者不该装在一起的工作，可以拆给多个**子 Agent**（sub-agent）：

- 每个子 Agent 有自己独立的上下文窗口，可以放开去搜索、读文件、试错；
- 完成后只把**精简的结论**交回主 Agent。Anthropic 的文章里提到，子 Agent 可能消耗了几万甚至更多 token，但返回的通常只是 1,000～2,000 token 的摘要；
- 主 Agent 的窗口里只有目标、计划和各个子任务的结论，不会被探索过程中的大量中间结果污染。

Anthropic 的多 Agent 研究系统就是这样设计的：主 Agent 规划，多个子 Agent 并行检索。他们公布的内部评测中，这套系统比单个 Agent 的表现高出 90.2%。但代价也很明显：多 Agent 系统消耗的 token 大约是普通对话的 15 倍（单 Agent 约 4 倍）。

所以隔离适合**可以拆分、可以并行、中间过程很重但结论很轻**的任务，比如广泛的调研、在大代码库里找东西。如果子任务之间需要频繁共享细节、互相依赖，拆开反而容易出现「各说各话」（详见本系列《多 Agent 协作》）。

隔离不一定非要用子 Agent。把大块数据放进**代码执行沙箱**的变量里，只把计算结果（比如统计值、筛选后的几行）交给模型，也是一种隔离。Anthropic 的「程序化工具调用」（Programmatic Tool Calling）就是这个思路：模型写一段代码去调用多个工具、处理中间结果，只有最终输出进入上下文。

## 工具结果：上下文最大的来源

在大多数 Agent 里，上下文增长最快的不是对话，而是**工具结果**。读一个文件几百行，搜一次几十条，跑一次测试几百行输出。所以管住工具结果，往往是最立竿见影的优化。

Anthropic 在《Writing effective tools for agents》中给出了一些建议，并提到 Claude Code 默认把单次工具返回限制在 25,000 token 以内。结合常见实践，可以整理成下面这张表：

| 做法 | 例子 | 说明 |
|---|---|---|
| **分页** | `list_orders(page=2, page_size=20)` | 默认只返回一页，并告诉模型「共 N 条，还有下一页」 |
| **范围读取** | `read_file(path, offset=120, limit=40)` | 已经知道行号时只读那一段，不读整个文件 |
| **过滤** | `search_logs(level="ERROR", since="10:00")` | 让工具在服务端过滤，不要把全量返回给模型再让它「找」 |
| **只返回必要字段** | 返回 `name`、`status`，不返回完整的原始 JSON | 少用 UUID、内部编号这类对模型意义不大的字段 |
| **截断并给出提示** | 「已截断，共 3,000 行，可用 grep 或行号范围继续读」 | 截断时告诉模型怎么拿到剩下的内容 |
| **详略两档** | `response_format: "concise" / "detailed"` | 让模型按需要选择；Anthropic 的例子里简略版约为详细版 token 的三分之一 |
| **有用的错误信息** | 「参数 date 格式应为 YYYY-MM-DD」 | 比一整段堆栈更省 token，也更容易让模型改对 |

两个原则：

1. **工具的默认值要保守**。模型通常不会主动传 `limit` 参数，默认值就决定了大多数情况下返回多少；
2. **截断要「可继续」**。只说「已截断」，模型不知道下一步怎么办；告诉它总量和获取剩余部分的方法，它就能按需继续读。

还有一点容易被忽视：**失败的尝试不要急着清掉**。Manus 团队的经验是，把错误的动作和报错信息留在上下文里，模型会据此调整，避免重复犯同样的错。可以清理的是那些「已经用完、结论已经记下」的成功结果，而不是「告诉模型此路不通」的信息。

## 排列顺序与提示词缓存

<figure>
<svg viewBox="0 0 440 332" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="排列顺序与缓存命中">
  <rect width="440" height="332" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif">
    <text x="220" y="30" fill="#7dd3fc" font-size="18" font-weight="800" text-anchor="middle">缓存按「前缀」命中</text>
    <text x="20" y="62" fill="#f4ede4" font-size="14" font-weight="700">做法 A：不变的在前，只往后追加</text>
    <g font-size="13" text-anchor="middle">
      <text x="14" y="91" fill="#9a93a8" text-anchor="start">1</text>
      <rect x="28" y="72" width="70" height="28" fill="rgba(125,211,252,.30)" stroke="#7dd3fc"/><text x="63" y="91" fill="#f4ede4">工具</text>
      <rect x="98" y="72" width="80" height="28" fill="rgba(125,211,252,.30)" stroke="#7dd3fc"/><text x="138" y="91" fill="#f4ede4">系统</text>
      <rect x="178" y="72" width="90" height="28" fill="rgba(125,211,252,.30)" stroke="#7dd3fc"/><text x="223" y="91" fill="#f4ede4">历史</text>
      <rect x="268" y="72" width="70" height="28" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/><text x="303" y="91" fill="#f4ede4">新消息</text>
      <text x="14" y="131" fill="#9a93a8" text-anchor="start">2</text>
      <rect x="28" y="112" width="310" height="28" fill="rgba(125,211,252,.30)" stroke="#7dd3fc"/><text x="183" y="131" fill="#f4ede4">和第 1 次完全相同的前缀</text>
      <rect x="338" y="112" width="84" height="28" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/><text x="380" y="131" fill="#f4ede4">新增内容</text>
    </g>
    <text x="28" y="164" fill="#7dd3fc" font-size="13">蓝色部分命中缓存，只有新增部分需要重新计算</text>
    <line x1="14" y1="184" x2="426" y2="184" stroke="rgba(255,255,255,.12)" stroke-dasharray="6 6"/>
    <text x="20" y="214" fill="#f4ede4" font-size="14" font-weight="700">做法 B：把时间戳放在最前面</text>
    <g font-size="13" text-anchor="middle">
      <text x="14" y="243" fill="#9a93a8" text-anchor="start">1</text>
      <rect x="28" y="224" width="70" height="28" fill="rgba(249,168,212,.22)" stroke="#f9a8d4"/><text x="63" y="243" fill="#f4ede4">10:01</text>
      <rect x="98" y="224" width="240" height="28" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/><text x="218" y="243" fill="#f4ede4">工具 · 系统 · 历史 · 新消息</text>
      <text x="14" y="283" fill="#9a93a8" text-anchor="start">2</text>
      <rect x="28" y="264" width="70" height="28" fill="rgba(249,168,212,.22)" stroke="#f9a8d4"/><text x="63" y="283" fill="#f4ede4">10:02</text>
      <rect x="98" y="264" width="324" height="28" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/><text x="260" y="283" fill="#f4ede4">工具 · 系统 · 历史 · 新增内容</text>
    </g>
    <text x="28" y="312" fill="#f9a8d4" font-size="13">开头就不同，后面内容再一样也无法命中</text>
  </g>
</svg>
<figcaption>缓存只认「从头开始完全相同」的部分，开头任何一点变化都会让后面全部失效</figcaption>
</figure>

### 提示词缓存是什么

模型处理输入时，会为每个 token 计算一组中间结果（注意力里的 Key 和 Value，即 KV Cache，见本系列《Token 与 KV Cache》）。如果两次请求的**开头部分完全相同**，这部分的计算结果就可以复用，不必重新算。各家厂商把它做成了「提示词缓存」（prompt caching）：命中缓存的输入 token 更便宜，首个 token 的延迟也更低。

关键词是**前缀**：缓存从第一个 token 开始逐个比对，直到遇到第一个不同的地方为止。前面哪怕只改了一个字，后面的内容再一样也用不上缓存。

而 Agent 的上下文，恰好天然适合缓存：每一步都是「上一步的全部内容 + 新增的一段」。只要遵守**只追加、不修改**，前一步的整个上下文就是下一步的前缀。Manus 团队甚至把 KV 缓存命中率称为生产环境 Agent「最重要的单一指标」，因为它同时决定了成本和延迟。他们举的例子是：在 Claude Sonnet 上，缓存命中的输入价格是 0.30 美元 / 百万 token，未命中是 3 美元，相差 10 倍。

### 主流厂商的缓存机制（大意）

各家的细节和价格随模型变化较快，下表只列大意，具体数字以官方文档为准（核实时间：2026 年 10 月）：

| | Anthropic（Claude） | OpenAI | Google（Gemini） |
|---|---|---|---|
| 是否自动 | 需要用 `cache_control` 标记缓存断点（也支持在请求顶层开启自动断点） | 支持的模型默认自动开启 | Gemini 2.5 及之后的模型默认开启隐式缓存；部分模型另有显式缓存 |
| 前缀顺序 | 按 工具定义 → 系统提示 → 消息 的顺序构成前缀 | 官方建议把指令、工具定义等不变内容放前面，动态内容放最后 | 官方建议把大段公共内容放在提示词开头 |
| 最短长度 | 因模型而异，从数百到数千 token 不等 | 新模型要求可缓存前缀至少 1,024 token | 因模型而异，如 2.5 Flash / Pro 为 2,048 token |
| 有效期 | 默认 5 分钟，每次命中刷新；可选 1 小时 | 因模型和设置而异，从几分钟到最长 24 小时 | 隐式缓存由平台管理 |
| 价格大意 | 写入为基础输入价的 1.25 倍（1 小时为 2 倍），读取约为 0.1 倍或更低 | 命中部分按折扣价计费，折扣因模型而异 | 命中部分自动打折 |
| 怎么看命中 | 响应里的 `cache_read_input_tokens` | `usage` 里的 `cached_tokens` | `usage` 里的缓存 token 字段 |

具体要求（比如 Anthropic 每次请求最多 4 个缓存断点，前缀检查最多回看 20 个内容块）都写在官方文档里。工程上真正重要的，是下面这几条共同的规律。

### 怎么排，才能命中缓存

1. **稳定的放前面，变化的放后面**：工具定义 → 系统提示 → 项目说明等长期不变的内容 → 对话历史 → 本轮新内容；
2. **不要在开头放时间戳**：系统提示里写「当前时间：10:02:17」，每次请求都不一样，等于每次都从头重算。确实需要时间，就放到最后的消息里；
3. **序列化要确定**：同样的数据，JSON 的键顺序、空格每次都要一样。有些语言的字典遍历顺序不固定，会悄悄破坏缓存；
4. **运行中不要增删工具**：工具定义在前缀的最前面，改一个就全部失效。需要限制模型能用的工具时，优先用 `tool_choice`、允许列表或解码时屏蔽（Manus 的做法），而不是从列表里删掉；
5. **历史只追加，不回头改**：修改或删除前面的某条消息，从那里往后的缓存都会失效。

这里有一个**取舍**：上一节讲的清理工具结果、摘要压缩，都会改动已有的上下文，必然让一部分缓存失效。所以压缩不宜「每步做一点」，而应该攒够一定量再一次性做。Anthropic 的 context editing 就提供了「每次至少清理多少 token」的参数，用意正是让每次失效都「值得」。

另一个看起来的矛盾是：长上下文研究建议把关键问题放在**末尾**（Anthropic 的长上下文提示建议中提到，把问题放在长文档之后，在测试中回答质量最多可提升约 30%），而缓存要求把不变的内容放在**开头**。两者其实不冲突：稳定的内容在前面吃缓存，当前目标和状态在末尾「复述」一遍吃注意力。Manus 反复改写 `todo.md`，就是同时满足这两点的做法。

### 实验：三种排法的前缀复用率

下面用一个小脚本模拟 5 轮请求，比较三种排法和上一轮相同的前缀有多少。这只是按字符比较前缀，用来说明原理，真实的缓存还有最短长度、断点位置等规则：

```python
import math, os, re

CJK = re.compile(r"[　-〿一-鿿＀-￯]")
def estimate_tokens(text):                                     # token 粗估，方法见下一节
    cjk = len(CJK.findall(text))
    return math.ceil(cjk + (len(text) - cjk) / 4)

SYSTEM = "你是后端排障助手。" + "工作规范……" * 300           # 一段很长、不变的系统提示
TOOLS = "工具定义：read_log、read_file、run_tests……" * 40       # 不变的工具定义

def build(layout, turn, history):
    now = f"当前时间 2026-10-15 10:{turn:02d}:00。"
    if layout == "时间戳放最前":
        return now + SYSTEM + TOOLS + history
    if layout == "工具每轮重排":                               # 比如按「最近用过」把工具排序
        tools = TOOLS if turn % 2 else TOOLS[::-1]
        return SYSTEM + tools + history + now
    return SYSTEM + TOOLS + history + now                      # 稳定前缀在前，变化的在最后

def shared_prefix_tokens(a, b):
    return estimate_tokens(a[:len(os.path.commonprefix([a, b]))])

for layout in ["时间戳放最前", "工具每轮重排", "稳定前缀在前"]:
    prev, history, hit, total = "", "", 0, 0
    for turn in range(1, 6):
        history += f"\n第{turn}轮：调用工具，得到结果……"            # 只追加，不改旧内容
        req = build(layout, turn, history)
        hit += shared_prefix_tokens(prev, req) if prev else 0
        total += estimate_tokens(req)
        prev = req
    print(f"{layout}：5 轮共输入 {total} tokens，和上一轮相同的前缀 {hit} tokens，占 {hit / total:.0%}")
```

输出：

```text
时间戳放最前：5 轮共输入 9840 tokens，和上一轮相同的前缀 32 tokens，占 0%
工具每轮重排：5 轮共输入 9840 tokens，和上一轮相同的前缀 5436 tokens，占 55%
稳定前缀在前：5 轮共输入 9840 tokens，和上一轮相同的前缀 7806 tokens，占 79%
```

三种排法发送的内容总量完全一样，差别只在顺序：

- **时间戳放最前**：每轮只有「当前时间 2026-10-15 10:0」这几个字符相同，几乎完全无法复用；
- **工具每轮重排**：系统提示还能复用，但工具定义和后面的历史全部失效；
- **稳定前缀在前**：只有第 1 轮需要全部计算，之后每轮只有新增的部分要重新算。第 1 轮无论如何都要完整计算，所以这里的 79% 已经接近 5 轮能达到的上限；轮数越多，比例越高。

## 动手：一个带「上下文预算」的 Agent 循环

<figure>
<svg viewBox="0 0 440 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="每轮发送的 token 数对比">
  <rect width="440" height="310" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif">
    <text x="220" y="28" fill="#7dd3fc" font-size="18" font-weight="800" text-anchor="middle">每轮送进模型的 token 数</text>
    <g font-size="13">
      <line x1="40" y1="48" x2="62" y2="48" stroke="#f9a8d4" stroke-width="3"/>
      <text x="68" y="53" fill="#f4ede4">不做管理（累计 18074）</text>
      <line x1="232" y1="48" x2="254" y2="48" stroke="#7dd3fc" stroke-width="3"/>
      <text x="260" y="53" fill="#f4ede4">带预算（累计 1689）</text>
    </g>
    <g stroke="rgba(255,255,255,.10)">
      <line x1="60" y1="240" x2="420" y2="240"/><line x1="60" y1="200" x2="420" y2="200"/>
      <line x1="60" y1="160" x2="420" y2="160"/><line x1="60" y1="120" x2="420" y2="120"/>
      <line x1="60" y1="80" x2="420" y2="80"/>
    </g>
    <g fill="#9a93a8" font-size="13" text-anchor="end">
      <text x="54" y="245">0</text><text x="54" y="205">1000</text><text x="54" y="165">2000</text>
      <text x="54" y="125">3000</text><text x="54" y="85">4000</text>
    </g>
    <polyline points="90,237 154,114 218,108 282,107 346,76 410,74" fill="none" stroke="#f9a8d4" stroke-width="3"/>
    <polyline points="90,237 154,231 218,226 282,224 346,228 410,226" fill="none" stroke="#7dd3fc" stroke-width="3"/>
    <g fill="#f9a8d4"><circle cx="90" cy="237" r="4"/><circle cx="154" cy="114" r="4"/><circle cx="218" cy="108" r="4"/><circle cx="282" cy="107" r="4"/><circle cx="346" cy="76" r="4"/><circle cx="410" cy="74" r="4"/></g>
    <g fill="#7dd3fc"><circle cx="154" cy="231" r="4"/><circle cx="218" cy="226" r="4"/><circle cx="282" cy="224" r="4"/><circle cx="346" cy="228" r="4"/><circle cx="410" cy="226" r="4"/></g>
    <text x="154" y="100" fill="#f9a8d4" font-size="13" text-anchor="middle">整份日志</text>
    <text x="346" y="214" fill="#7dd3fc" font-size="13" text-anchor="middle">压缩</text>
    <g fill="#9a93a8" font-size="13" text-anchor="middle">
      <text x="90" y="262">1</text><text x="154" y="262">2</text><text x="218" y="262">3</text>
      <text x="282" y="262">4</text><text x="346" y="262">5</text><text x="410" y="262">6</text>
      <text x="240" y="294">轮次（数据来自下面代码的真实输出）</text>
    </g>
  </g>
</svg>
<figcaption>同一个任务、同样的 6 轮：不做管理时每轮输入一路上涨，带预算时始终在 400 token 附近</figcaption>
</figure>

下面用 Python 标准库写一个最小的 Agent 循环，把前面讲的几件事串起来：

- **按 token 粗估计数**：不依赖任何分词器；
- **截断超长工具结果**：保留开头、结尾和含关键字的行，中间换成一句「怎么继续读」的提示；
- **超预算时压缩旧轮次**：只保留最近 2 轮原文，更早的轮次合并成摘要；
- **系统提示和任务目标永远排在最前**，不参与压缩；
- 每一轮打印上下文的构成，以及压缩前后的 token 数。

**关于 token 估算**。准确的 token 数要用对应模型的分词器来算，不同模型差别不小。粗估时常用的经验值：OpenAI 的帮助文档给出英文约 4 个字符 1 个 token；DeepSeek 的文档给出 1 个中文字符约 0.6 个 token、1 个英文字符约 0.3 个 token。做预算时**宁可高估**，所以这里把中文（含全角标点）按 1 字 1 token、其他字符按 4 个 1 token 计算。正式环境中，应该以接口返回的 `usage` 为准，或者调用厂商提供的计数接口。

这里用一个**假模型**代替真实 LLM：它按照固定的剧本，根据上下文里已经完成了几步，返回下一步的工具调用。摘要也用规则代替（每一步只保留意图和一行关键输出）。换成真实 API 时，只需替换 `fake_llm`（调用模型）和 `fake_summarize`（让模型写摘要）这两个函数。

```python
import math, re

# ---------- 1. token 粗估 ----------
CJK = re.compile(r"[　-〿一-鿿＀-￯]")

def estimate_tokens(text: str) -> int:
    """中文（含全角标点）按 1 字 1 token，其余字符按 4 个 1 token，宁可高估。"""
    cjk = len(CJK.findall(text))
    return math.ceil(cjk + (len(text) - cjk) / 4)

# ---------- 2. 假工具：故意返回很长的结果 ----------
def tool_read_log(_):
    lines = [f"2026-10-15 10:{i // 60:02d}:{i % 60:02d} INFO order-svc GET /orders/{1000 + i} 200 12ms"
             for i in range(200)]
    lines[137] = "2026-10-15 10:02:17 ERROR order-svc NullPointerException at PriceCalculator.java:42"
    return "\n".join(lines)

def tool_read_file(arg):                         # 支持 "文件名#L起-止"，只读一段
    name, _, rng = arg.partition("#L")
    body = [f"{i:>3}  // {name} 普通业务代码" for i in range(1, 61)]
    body[41] = " 42  return price - coupon.getAmount();"
    lo, hi = map(int, rng.split("-")) if rng else (1, 60)
    return "\n".join(body[lo - 1:hi])

def tool_run_tests(_):
    return "Ran 48 tests: 47 passed, 1 failed (test_order_without_coupon)"

TOOLS = {"read_log": tool_read_log, "read_file": tool_read_file, "run_tests": tool_run_tests}

# ---------- 3. 假模型：按「已经做了几步」返回固定动作 ----------
SCRIPT = [
    ("先看错误日志", "read_log", "order-svc.log"),
    ("日志里有 NPE，只读出错位置附近", "read_file", "PriceCalculator.java#L38-46"),
    ("第 42 行没判空，跑测试复现", "run_tests", ""),
    ("看调用方是否会传入空 coupon", "read_file", "OrderService.java"),
    ("改成 coupon 为空时不减价，重跑测试", "run_tests", ""),
]

def fake_llm(context: list) -> dict:
    """代替真实 LLM：数一数上下文里做过几步，返回剧本里的下一步。换成真实 API 只需替换这个函数。"""
    done = sum(m["role"] == "assistant" for m in context)
    done += sum(m["content"].count("\n- 第") for m in context if m["role"] == "summary")
    if done < len(SCRIPT):
        thought, tool, arg = SCRIPT[done]
        return {"thought": thought, "tool": tool, "arg": arg}
    return {"final": "PriceCalculator 第 42 行对 coupon 判空后，48 个测试全部通过"}

KEY = re.compile(r"ERROR|failed|coupon")

def fake_summarize(turns: list) -> str:
    """代替「让模型写摘要」：每一步只留意图 + 关键输出行，丢掉原始工具输出。"""
    out = []
    for call, result in zip(turns[::2], turns[1::2]):
        out.append(f"\n- 第{call['step']}步 {call['tool']}：{call['thought']}")
        out += [f"\n  关键输出：{l.strip()}" for l in result["content"].splitlines() if KEY.search(l)][:1]
    return "".join(out)

# ---------- 4. 上下文管理 ----------
BUDGET, TOOL_MAX, KEEP_RECENT = 400, 200, 2   # 总预算 / 单条工具结果上限 / 保留最近几轮原文

def tokens(msgs):
    return sum(estimate_tokens(m["content"]) for m in msgs)

def truncate_tool_result(text: str) -> str:
    """超长结果：保留开头、结尾和含关键字的行，中间换成一句提示。"""
    if estimate_tokens(text) <= TOOL_MAX:
        return text
    lines = text.splitlines()
    hits = [l for l in lines[3:-2] if KEY.search(l)]
    note = f"...[共 {len(lines)} 行，已省略 {len(lines) - 5 - len(hits)} 行；可用 grep 或行号范围继续读取]..."
    return "\n".join(lines[:3] + [note] + hits + lines[-2:])

def fit_budget(ctx):
    """超预算时：把最近 KEEP_RECENT 轮之前的轮次并入摘要；系统提示和目标永远排在最前。"""
    if tokens(ctx) <= BUDGET:
        return ctx, False
    fixed = [m for m in ctx if m["role"] in ("system", "goal")]
    summary = "".join(m["content"] for m in ctx if m["role"] == "summary") or "已完成的步骤："
    turns = [m for m in ctx if m["role"] in ("assistant", "tool")]
    old, recent = turns[:-2 * KEEP_RECENT], turns[-2 * KEEP_RECENT:]
    return fixed + [{"role": "summary", "content": summary + fake_summarize(old)}] + recent, True

def composition(ctx):
    parts = {"系统": 0, "目标": 0, "摘要": 0, "历史": 0}
    label = {"system": "系统", "goal": "目标", "summary": "摘要"}
    for m in ctx:
        parts[label.get(m["role"], "历史")] += estimate_tokens(m["content"])
    return "  ".join(f"{k} {v:>3}" for k, v in parts.items())

# ---------- 5. Agent 循环 ----------
def run(manage: bool):
    ctx = [
        {"role": "system", "content": "你是后端排障助手。可用工具：read_log、read_file、run_tests。每次只调用一个工具，先定位再修改。"},
        {"role": "goal", "content": "任务：订单服务今天 10 点后偶发 500，找到原因并修复，修复后测试必须全部通过。"},
    ]
    sent = []
    for step in range(1, 10):
        before = tokens(ctx)
        if manage:
            ctx, squeezed = fit_budget(ctx)
            print(f"第{step}轮 压缩前 {before:>4} → 发送 {tokens(ctx):>3} | {composition(ctx)}"
                  + ("  ← 触发压缩" if squeezed else ""))
        sent.append(tokens(ctx))
        act = fake_llm(ctx)
        if "final" in act:
            print("最终回答:", act["final"])
            break
        result = TOOLS[act["tool"]](act["arg"])
        if manage and estimate_tokens(result) > TOOL_MAX:
            short = truncate_tool_result(result)
            print(f"       {act['tool']} 返回 {estimate_tokens(result)} tokens → 截断为 {estimate_tokens(short)}")
            result = short
        ctx.append({"role": "assistant", "content": f"{act['thought']} → {act['tool']}({act['arg']})",
                    "step": step, **act})
        ctx.append({"role": "tool", "content": result})
    return sent, ctx

print("=== 不做任何管理 ===")
naive, _ = run(manage=False)
print("每轮发送:", " → ".join(map(str, naive)), f"，累计输入 {sum(naive)} tokens\n")

print(f"=== 带上下文预算：总预算 {BUDGET}，单条工具结果上限 {TOOL_MAX} ===")
managed, ctx = run(manage=True)
print("每轮发送:", " → ".join(map(str, managed)),
      f"，累计输入 {sum(managed)} tokens（约为前者的 {sum(managed) / sum(naive):.0%}）")

print("\n最终上下文的排列:", " → ".join(m["role"] for m in ctx))
print("摘要内容:", next(m["content"] for m in ctx if m["role"] == "summary"))
```

输出（Python 3.13）：

```text
=== 不做任何管理 ===
最终回答: PriceCalculator 第 42 行对 coupon 判空后，48 个测试全部通过
每轮发送: 77 → 3146 → 3289 → 3321 → 4103 → 4138 ，累计输入 18074 tokens

=== 带上下文预算：总预算 400，单条工具结果上限 200 ===
第1轮 压缩前   77 → 发送  77 | 系统  41  目标  36  摘要   0  历史   0
       read_log 返回 3056 tokens → 截断为 123
第2轮 压缩前  213 → 发送 213 | 系统  41  目标  36  摘要   0  历史 136
第3轮 压缩前  356 → 发送 356 | 系统  41  目标  36  摘要   0  历史 279
第4轮 压缩前  388 → 发送 388 | 系统  41  目标  36  摘要   0  历史 311
       read_file 返回 762 tokens → 截断为 99
第5轮 压缩前  507 → 发送 310 | 系统  41  目标  36  摘要  82  历史 151  ← 触发压缩
第6轮 压缩前  345 → 发送 345 | 系统  41  目标  36  摘要  82  历史 186
最终回答: PriceCalculator 第 42 行对 coupon 判空后，48 个测试全部通过
每轮发送: 77 → 213 → 356 → 388 → 310 → 345 ，累计输入 1689 tokens（约为前者的 9%）

最终上下文的排列: system → goal → summary → assistant → tool → assistant → tool → assistant → tool
摘要内容: 已完成的步骤：
- 第1步 read_log：先看错误日志
  关键输出：2026-10-15 10:02:17 ERROR order-svc NullPointerException at PriceCalculator.java:42
- 第2步 read_file：日志里有 NPE，只读出错位置附近
  关键输出：42  return price - coupon.getAmount();
```

逐段解读：

- **不做管理时**：第 1 步把 200 行日志整份读进来，上下文从 77 token 直接跳到 3,146；第 4 步又整份读了一个文件。此后每一轮都要把这些内容重新发一遍，6 轮累计输入 18,074 token；
- **截断工具结果**：日志从 3,056 token 截到 123，保留了开头 3 行、结尾 2 行和唯一的 ERROR 行。模型要的信息就是那一行，其余 199 行都是噪音；
- **范围读取**：第 2 步假模型用 `PriceCalculator.java#L38-46` 只读了 9 行，结果本来就很短，不需要截断。这比「先读全部再截断」更好：工具层面就没有产生多余内容；
- **触发压缩**：第 5 轮压缩前是 507 token，超过 400 的预算，于是前 2 轮被合并成 82 token 的摘要，发送量降到 310。系统提示（41）和目标（36）始终原样排在最前；
- **摘要保留了什么**：每一步的意图，加上一行关键输出（NPE 的位置、第 42 行的代码）。原始日志和文件内容都没有了，但定位问题所需的事实都在；
- **结果**：两种方式得到同样的结论，带预算的版本累计输入只有不管理时的约 9%。

这个例子刻意做得很小。真实系统里预算会是几万到十几万 token，摘要由模型来写，但结构是一样的：**固定部分 + 摘要 + 最近几轮原文**。

还有两点值得注意：

1. 压缩会改动上下文，让缓存失效。这里的预算很紧，第 5 轮就压缩了一次；真实系统应该把阈值设得足够高，让压缩不频繁发生，并且一次压掉较多内容；
2. 关键字匹配只是演示。在 `truncate_tool_result` 里，如果关键行不包含 ERROR、failed、coupon 这几个词，就会被截掉。真实的工具应该优先在服务端做过滤和范围读取，截断只是兜底。

## 长任务中的上下文管理

当任务长到一个窗口无论如何都装不下（比如几个小时的编码、跨越多个会话的项目），就需要更系统的办法。

### 压缩（compaction）

**压缩**是指在上下文接近上限时，让模型把到目前为止的对话总结成一段摘要，然后用「摘要 + 最近的内容」开启一个新的窗口继续工作。

- **Claude Code 的做法**：Anthropic 在文章中介绍，Claude Code 会把消息历史交给模型总结，保留架构决定、未解决的 bug、实现细节，丢掉重复的工具输出，然后带着压缩后的上下文和**最近访问过的 5 个文件**继续工作；
- **API 层面的支持**：一些厂商已经把压缩做成了 API 的服务端能力，在输入超过设定阈值时自动生成摘要并替换之前的内容，开发者可以自定义摘要的提示词；
- **摘要提示词怎么写**：Anthropic 的建议是，先追求**召回**，确保所有关键信息都留下来，再逐步删掉多余的部分。

摘要最危险的地方是**悄悄丢掉关键信息**。尤其是这几类：

| 容易丢的信息 | 后果 | 对策 |
|---|---|---|
| 用户提出的约束（「不要改公共接口」） | 后面的步骤违反约束 | 约束写进固定的「目标」区，不参与压缩 |
| 已经排除的方案（「方案 A 试过，不行」） | 重复踩坑 | 摘要提示词里明确要求保留失败的尝试及原因 |
| 精确数值、路径、版本号 | 摘要里只剩「某个文件」「一个较大的值」 | 要求原样保留标识符；或者写入外部文件 |
| 未完成的子任务 | 以为已经做完 | 待办清单放在文件里，而不是只存在于对话中 |

Anthropic 的 cookbook 里有一个观察：经过自动压缩后，高层次的事实（比如关键数字、研究对象）大多被保留了，而附录表格里的细节数值没有被保留。**摘要天然有损**，能写进文件的关键信息，不要只指望摘要。

### 进度文件：给下一个会话的交接单

压缩解决的是「一个会话内」的问题。如果任务要跨越多个会话（每次开新会话，上下文都是空的），就需要像交接班一样，把进度写在外部。

Anthropic 在《Effective harnesses for long-running agents》中介绍过一种做法：

- 第一个会话由「初始化 Agent」负责：把需求展开成一份**功能清单**（JSON 格式，每一项默认标记为未通过），写一个启动开发环境的脚本，创建**进度日志文件**（`claude-progress.txt`），并做第一次 git 提交；
- 之后的每个会话由「编码 Agent」负责：开始时先看工作目录、读 git 日志和进度文件、读功能清单，挑一个最高优先级的未完成功能；**一次只做一个功能**，做完提交代码、更新进度；
- 他们选 JSON 而不是 Markdown 存功能清单，是因为模型不太容易随手改坏 JSON 格式的文件。

这个方案解决了两个典型的失败：一是 Agent 想一口气做完所有事，结果做到一半上下文耗尽，下一个会话接手的是半成品；二是后来的会话看到已经有不少进展，就宣布「完成了」。

可以看出，这和人类团队的工作方式很像：**需求清单、进度记录、代码提交历史**，就是最好的「外部上下文」。git 日志本身就是一份结构化、可检索、不会被压缩丢失的历史记录（详见本系列《规划与长任务》）。

### 几种手段怎么组合

| 问题 | 手段 | 特点 |
|---|---|---|
| 大块的、可以重新获取的工具结果占满窗口 | 清理旧工具结果 | 最便宜，几乎无损（需要时重新调用） |
| 对话和推理过程本身越来越长 | 摘要压缩 | 覆盖所有内容，但有损 |
| 关键信息要跨会话保留 | 记忆、进度文件 | 唯一能跨会话的办法，但不减少单个会话内的增长 |
| 某些子任务的中间过程特别重 | 子 Agent 隔离 | 主窗口干净，但总 token 更多 |

实践中通常是组合使用：先清理工具结果，还不够再做摘要压缩，重要的发现随时写入文件。

## 常见的坑

### 1. 工具定义太多

接了七八个 MCP 服务器，几十上百个工具全部放进去。后果不只是 token 多：工具之间名字和功能相近，模型更容易选错。

做法：只放当前任务需要的工具；工具多时用工具搜索、按需加载；相关的工具用统一前缀命名（如 `github_`、`jira_`），描述写清楚「什么时候用、什么时候不用」。

### 2. 把整份日志、整个文件塞进去

一次 `cat` 几千行日志，或者把一个大接口的完整 JSON 原样返回。这是上下文膨胀最常见的原因。

做法：工具默认分页、默认限制行数；提供 grep、按级别过滤、按行号范围读取等能力；返回结果时只保留必要字段。

### 3. 历史无限增长

很多简单的 Agent 实现只有一个 `messages.append()`，从来不删。短任务没问题，长任务迟早出事：先是变慢变贵，然后是效果下降，最后撞上限报错。

做法：给上下文设预算，监控每一步的 token 数；超过阈值先清理旧工具结果，再做摘要压缩。

### 4. 摘要丢掉关键约束

这就是开头那个例子。压缩之后，「不要修改公共接口」这条要求没有被写进摘要，后面的步骤自然不知道。

做法：把任务目标和硬性约束放在固定区域，永远不参与压缩；摘要提示词里列出必须保留的信息类型；压缩后可以用测试用例检查关键信息是否还在。

### 5. 破坏缓存的小改动

在系统提示开头放时间戳、每次请求随机打乱工具顺序、JSON 序列化的键顺序不稳定、运行中途增删工具。这些改动看起来无害，却会让缓存命中率接近零，成本和延迟成倍上升。

做法：把缓存命中率当作一个监控指标；在测试里比较连续两次请求的前缀是否一致。

### 6. 检索塞得太多、互相矛盾

为了「保险」，一次召回 20 段文档全部塞进去，其中有过时的版本、有互相矛盾的说法。LangChain 的博客引用了几种常见的上下文失败类型：**上下文中毒**（错误信息进入上下文并被反复引用）、**上下文干扰**（内容太多，盖过了模型本身的判断）、**上下文混淆**（无关内容影响了回答）、**上下文冲突**（上下文中的内容互相矛盾）。

做法：控制召回数量，做重排和去重；文档带上来源和时间；冲突的信息要么在进入上下文之前解决，要么明确告诉模型以哪个为准。

### 7. 历史太「整齐」，模型开始模仿

Manus 团队提到过一个现象：上下文里全是格式完全一样的「动作—结果」记录时，模型会倾向于照着这个模式继续，即使已经不合适。比如批量审阅 20 份简历，后面几份开始机械重复前面的处理方式。

做法：在序列化方式、措辞上引入少量有规律的变化，打破过于单一的模式。

### 8. 不测量就优化

上下文工程的很多决定（保留几轮、阈值设多少、摘要怎么写）没有通用答案。凭感觉调，容易一边省了 token，一边悄悄降低了成功率。

做法：记录每一步的上下文构成和 token 数，用一组固定的任务做评测，比较改动前后的成功率和成本（见本系列《评估（Evals）》和《Agent 的成本与延迟》）。

## 高频面试题速答

**Q：上下文工程和提示词工程有什么区别？**
提示词工程关注一段指令怎么写；上下文工程关注 Agent 每一步送进模型的全部内容：系统提示、工具定义、历史、工具结果、检索文档、记忆、任务状态，以及它们放多少、怎么排、何时清理。前者是后者的一部分。

**Q：上下文窗口那么大，为什么还要管理？**
四个原因：有硬上限；每一步都要为整个上下文付费，累计成本随步数近似平方增长；输入越长，延迟越高；内容越多，注意力越分散，「中间遗忘」等研究表明长输入中间的信息更容易被忽略。

**Q：什么是 Lost in the Middle？**
Liu et al. 的研究发现，模型在长输入中利用信息的能力和位置有关：相关信息在开头或结尾时效果最好，在中间时明显变差，呈 U 形曲线。启示是关键信息不要埋在中间，并且尽量减少无关内容。

**Q：上下文管理有哪些策略？**
写入（把笔记、待办、记忆存到外部文件）、选择（按需检索、按需加载工具和技能）、压缩（清理旧工具结果、截断、摘要）、隔离（子 Agent 用独立的上下文，只返回精简结果）。

**Q：怎么提高提示词缓存命中率？**
稳定的内容（工具定义、系统提示）放在最前面，动态内容（时间、当前问题）放在最后；历史只追加不修改；序列化保持确定；运行中不增删工具；压缩不要太频繁，攒够一定量再做。

**Q：工具返回的结果太长怎么办？**
在工具层面解决：分页、按范围读取、服务端过滤、只返回必要字段、提供简略和详细两种格式；截断时告诉模型总量和继续读取的方法。已经用过的旧结果可以清理，失败的尝试和报错最好保留。

**Q：摘要压缩有什么风险，怎么降低？**
摘要有损，容易丢掉用户约束、已排除的方案、精确的数值和路径。对策：目标和约束放在固定区域不参与压缩；摘要提示词明确列出必须保留的内容；关键信息同时写入外部文件。

**Q：什么时候该用子 Agent？**
任务可以拆分、可以并行，且中间过程很重但结论很轻时，比如大范围调研、在大代码库里搜索。代价是总 token 消耗更高，子任务之间需要频繁共享细节时不适合。

## 总结

- Agent 每一步的全部认知，就是此刻上下文窗口里的内容。**上下文工程**管的是这块窗口里放什么、放多少、怎么排；
- 上下文由系统提示、工具定义、记忆、检索文档、对话历史、工具结果、任务状态组成，后几类会在运行中不断增长；
- 窗口**有限且昂贵**：硬上限、累计成本、延迟，以及越长越不准（中间遗忘、上下文腐烂）。窗口大小是上限，不是目标；
- 四种策略：**写入**（存到外部）、**选择**（按需拉进来）、**压缩**（清理、截断、摘要）、**隔离**（子 Agent 各用各的窗口）；
- 工具结果是最大的来源：分页、范围读取、过滤、精简字段，截断时说明怎么继续；
- **稳定前缀在前、只追加不修改**，才能吃到提示词缓存；当前目标可以在末尾再复述一遍；
- 长任务靠**压缩 + 外部文件**：摘要会丢信息，约束、待办、进度要写在文件里；
- 所有阈值和做法都要用数据验证：记录每一步的上下文构成，用评测比较成功率和成本。

<div class="refs" markdown="1">

### 参考资料

- Anthropic Engineering (2025). Effective context engineering for AI agents.
- Anthropic Engineering (2025). Writing effective tools for agents — with agents.
- Anthropic Engineering (2025). How we built our multi-agent research system.
- Anthropic Engineering (2025). Advanced tool use（Tool Search Tool、Programmatic Tool Calling）.
- Anthropic Engineering (2025). Equipping agents for the real world with Agent Skills.
- Anthropic Engineering (2025). Effective harnesses for long-running agents.
- Anthropic (2025). Context management（context editing 与 memory tool 发布说明）.
- Claude 官方文档：Prompt caching；Long context prompting tips；Claude Cookbook: Context engineering tools.
- OpenAI 官方文档：Prompt caching；OpenAI Help Center: What are tokens and how to count them.
- Google Gemini API 文档：Context caching.
- DeepSeek API 文档：Token 用量计算.
- Liu, N. F., et al. (2024). Lost in the Middle: How Language Models Use Long Contexts. *Transactions of the Association for Computational Linguistics*, 12. arXiv:2307.03172.
- Chroma Research (2025). Context Rot（技术报告）.
- LangChain Blog (2025). Context Engineering for Agents.
- Manus Blog (2025). Context Engineering for AI Agents: Lessons from Building Manus.

</div>
