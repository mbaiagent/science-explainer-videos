title: 多 Agent 协作：什么时候该让 AI 组队
subtitle: 单 Agent 的三个瓶颈，主管-工人、并行扇出、流水线、生成者-评审者、交接五种拓扑，子 Agent 的上下文隔离与并行，派单怎么写、结果怎么汇总与处理冲突，token 与协调的代价，业界的正反经验，评估与追踪，附一个并行调研的 orchestrator 和一个评审循环
tag: AI 与大模型
color: #a7f3d0

## 两篇前后脚发表的文章

2025 年 6 月，两家做 Agent 的公司在相隔一天的时间里各发了一篇工程博客。

一篇来自 Cognition（做编程 Agent Devin 的公司），标题很直接：**Don't Build Multi-Agents**（不要构建多 Agent）。文章认为，把一个任务拆给多个并行的 Agent，它们各自做出的隐含决定会互相冲突，最后拼不到一起。

另一篇来自 Anthropic，介绍他们怎么搭建 Claude 的多 Agent 研究系统：一个主 Agent 负责规划，多个子 Agent 并行搜索。在他们的内部调研评测上，这套系统比单个 Agent 的表现**高出 90.2%**。

一个说别做，一个说做了效果大涨。到底该听谁的？

仔细读下去会发现，两篇文章并不矛盾，它们讨论的是**不同形状的任务**。Anthropic 做的是广度优先的调研：要查的方向很多、彼此独立，每个方向都要读大量网页，但最后只需要几句结论。Cognition 做的是写代码：每一处改动都和其他改动紧密相关，一个 Agent 定下的命名、风格、接口，另一个 Agent 必须知道。

所以真正的问题不是「多 Agent 好不好」，而是：**什么样的任务值得拆、怎么拆、拆完要付出什么代价**。这篇文章就围绕这三个问题展开。

> 本文默认你已经了解 Agent 的基本循环（模型 → 调用工具 → 结果追加回上下文 → 再调用模型）。不熟悉的话，可以先看本系列《Agent 设计模式》和《上下文工程》。

## 单 Agent 的三个瓶颈

<figure>
<svg viewBox="0 0 440 405" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="单 Agent 的三个瓶颈">
  <rect width="440" height="405" fill="#0f0e1c"/>
  <defs><marker id="ma-a1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9a93a8"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif">
    <text x="20" y="30" fill="#a7f3d0" font-size="16" font-weight="800">① 上下文装不下</text>
    <rect x="20" y="44" width="330" height="40" rx="6" fill="none" stroke="#9a93a8"/>
    <rect x="350" y="44" width="70" height="40" rx="6" fill="rgba(252,165,165,.16)" stroke="#fca5a5" stroke-dasharray="5 4"/>
    <g font-size="13" text-anchor="middle" fill="#f4ede4">
      <rect x="23" y="47" width="44" height="34" rx="4" fill="rgba(167,243,208,.30)"/>
      <text x="45" y="69">系统</text>
      <rect x="70" y="47" width="84" height="34" rx="4" fill="rgba(167,243,208,.16)"/>
      <text x="112" y="69">网页 1</text>
      <rect x="157" y="47" width="84" height="34" rx="4" fill="rgba(167,243,208,.16)"/>
      <text x="199" y="69">网页 2</text>
      <rect x="244" y="47" width="103" height="34" rx="4" fill="rgba(167,243,208,.16)"/>
      <text x="295" y="69">测试输出</text>
      <text x="385" y="69" fill="#fca5a5">溢出</text>
    </g>
    <text x="20" y="108" fill="#9a93a8" font-size="13">读得越多，窗口越满；开头的约束被淹没在中间结果里</text>

    <text x="20" y="150" fill="#a7f3d0" font-size="16" font-weight="800">② 只能一步一步来</text>
    <g font-size="13" text-anchor="middle" fill="#f4ede4">
      <rect x="20" y="164" width="90" height="34" rx="6" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="65" y="186">查方向 A</text>
      <rect x="114" y="164" width="90" height="34" rx="6" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="159" y="186">查方向 B</text>
      <rect x="208" y="164" width="90" height="34" rx="6" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="253" y="186">查方向 C</text>
      <rect x="302" y="164" width="118" height="34" rx="6" fill="rgba(167,243,208,.14)" stroke="#a7f3d0"/>
      <text x="361" y="186">写报告</text>
    </g>
    <line x1="20" y1="214" x2="418" y2="214" stroke="#9a93a8" stroke-width="2" marker-end="url(#ma-a1)"/>
    <text x="20" y="238" fill="#9a93a8" font-size="13">总耗时 = 每一步相加，等工具的时间全在关键路径上</text>

    <text x="20" y="280" fill="#a7f3d0" font-size="16" font-weight="800">③ 一个人身兼数职</text>
    <rect x="20" y="294" width="400" height="62" rx="12" fill="rgba(255,255,255,.04)" stroke="#9a93a8"/>
    <g font-size="14" text-anchor="middle" font-weight="700">
      <rect x="36" y="310" width="80" height="30" rx="15" fill="rgba(167,243,208,.16)" stroke="#a7f3d0"/>
      <text x="76" y="330" fill="#f4ede4">规划</text>
      <rect x="132" y="310" width="80" height="30" rx="15" fill="rgba(167,243,208,.16)" stroke="#a7f3d0"/>
      <text x="172" y="330" fill="#f4ede4">搜索</text>
      <rect x="228" y="310" width="80" height="30" rx="15" fill="rgba(167,243,208,.16)" stroke="#a7f3d0"/>
      <text x="268" y="330" fill="#f4ede4">写作</text>
      <rect x="324" y="310" width="80" height="30" rx="15" fill="rgba(252,165,165,.16)" stroke="#fca5a5"/>
      <text x="364" y="330" fill="#fca5a5">自己审</text>
    </g>
    <text x="20" y="384" fill="#9a93a8" font-size="13">提示词越写越长；自己审自己写的东西，容易放过错误</text>
  </g>
</svg>
<figcaption>单 Agent 的三个瓶颈：一个窗口、一条时间线、一套提示词</figcaption>
</figure>

假设你要让 Agent 做一份调研：「给公司的客服问答系统选一款向量数据库，从性能、成本、生态三个方面比较三个候选」。用一个 Agent 去做，会依次撞上三堵墙。

### 1. 上下文装不下

每读一个网页、每跑一次工具，结果都会追加到上下文里。三个方向、每个方向读几页文档，几十个工具结果叠在一起，很快就是几万甚至几十万 token。

这带来两个问题。一是**硬上限**：窗口满了就得截断或压缩，压缩可能丢掉关键约束。二是**注意力稀释**：即使没满，越长的上下文里，开头那句「只考虑能私有化部署的方案」越容易被忽略（见本系列《上下文工程》）。而且，第三个方向的调研根本用不上第一个方向读过的那几十页原文，它们占着窗口，却只是噪音。

### 2. 串行太慢

Agent 的循环是一步接一步的：调用模型、等工具返回、再调用模型。三个方向明明互不相关，却只能排队做。调研类任务的耗时大部分花在**等工具**上（搜索、抓网页、查数据库），这些等待全部落在关键路径上。

现代模型支持在一次回复里发出多个工具调用（并行工具调用），这能缓解一部分。但「先搜、再根据结果决定读哪页、再根据内容决定下一步搜什么」这种需要推理的链条，在一个 Agent 内部还是串行的。

### 3. 角色混杂

一个 Agent 要同时当规划者、搜索员、写手和审稿人。系统提示词里塞满了各种角色的规则，工具列表也越来越长。工具一多，模型选错工具的概率就会上升。

更麻烦的是**自己审自己**。让写出答案的同一个上下文去检查答案，它看到的是自己刚刚的推理过程，很容易被同样的思路说服，放过同样的错误。

### 先别急着拆

在把任务拆给多个 Agent 之前，值得先问一句：这些问题能不能在单 Agent 内部解决？

| 瓶颈 | 单 Agent 内的解法 | 什么时候还不够 |
|---|---|---|
| 上下文装不下 | 裁剪工具结果、摘要压缩、把资料写到文件里按需读取 | 每个方向本身就要读大量原文 |
| 串行太慢 | 并行工具调用 | 每个方向都要多轮「搜索 → 判断 → 再搜索」 |
| 角色混杂 | 精简提示词、按阶段切换工具集 | 需要一个没被生成过程「污染」的审稿人 |

Anthropic 在 2024 年底的《Building effective agents》里给过一条朴素的建议：**先找最简单的方案，只有在测量证明有提升时才增加复杂度**。多 Agent 是复杂度很高的一种方案，它应该是你「单 Agent 做不好」之后的选择，而不是起点。

## 多 Agent 系统是什么

把上面的定义说清楚：一个 **Agent** 是「模型 + 工具 + 循环」，它有自己的系统提示词、自己的工具集，以及最重要的，**自己的上下文窗口**。**多 Agent 系统**就是多个这样的循环，通过消息互相配合完成一个任务。

这里的关键词是「各自的上下文」。如果只是同一个对话里让模型「现在扮演审稿人」，那仍然是单 Agent，只是换了一段提示词。多 Agent 的本质区别在于：**每个 Agent 看到的东西不一样**。这既是它的价值来源（隔离），也是它的主要风险来源（信息不共享）。

谁来决定「下一步交给哪个 Agent」？有两种做法。OpenAI Agents SDK 的文档把它们称为「由 LLM 编排」和「由代码编排」：

| | 由 LLM 编排 | 由代码编排 |
|---|---|---|
| 谁做决定 | 主 Agent 在运行时决定拆几个子任务、派给谁 | 程序写死流程：先 A 后 B，或者 A、B、C 并行 |
| 优点 | 灵活，能处理事先想不到的任务形状 | 可预测：速度、成本、效果都更稳定 |
| 缺点 | 可能拆得太细或太粗，成本波动大 | 只能处理设计时想到的情况 |
| 例子 | 调研系统按问题复杂度决定开几个子 Agent | 固定的「检索 → 起草 → 审校」流水线 |

两种可以混用：外层用代码保证大流程，内层让模型自由发挥。Anthropic 在《Building effective agents》里做了类似的区分：由代码预先定好路径的叫**工作流**（workflow），由模型动态决定流程和工具使用的叫 **Agent**。

## 五种常见拓扑

<figure>
<svg viewBox="0 0 440 470" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="主管-工人、并行扇出、流水线三种拓扑">
  <rect width="440" height="470" fill="#0f0e1c"/>
  <defs><marker id="ma-a2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#a7f3d0"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="30" fill="#a7f3d0" font-size="16" font-weight="800">主管-工人：运行时决定拆几份、派给谁</text>
    <rect x="160" y="46" width="120" height="36" rx="10" fill="rgba(167,243,208,.16)" stroke="#a7f3d0"/>
    <text x="220" y="69" fill="#f4ede4" font-size="14" font-weight="700">主 Agent</text>
    <line x1="190" y1="82" x2="90" y2="114" stroke="#a7f3d0" stroke-width="2" marker-end="url(#ma-a2)"/>
    <line x1="220" y1="82" x2="220" y2="114" stroke="#a7f3d0" stroke-width="2" marker-end="url(#ma-a2)"/>
    <line x1="250" y1="82" x2="350" y2="114" stroke="#a7f3d0" stroke-width="2" marker-end="url(#ma-a2)"/>
    <g font-size="14" fill="#f4ede4">
      <rect x="30" y="116" width="110" height="34" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="85" y="138">子 Agent 1</text>
      <rect x="165" y="116" width="110" height="34" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="220" y="138">子 Agent 2</text>
      <rect x="300" y="116" width="110" height="34" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="355" y="138">子 Agent 3</text>
    </g>
    <text x="220" y="174" fill="#9a93a8" font-size="13">子任务的数量和内容由主 Agent 决定，结论交回主 Agent</text>

    <line x1="20" y1="192" x2="420" y2="192" stroke="rgba(255,255,255,.12)" stroke-dasharray="6 6"/>
    <text x="220" y="220" fill="#a7f3d0" font-size="16" font-weight="800">并行扇出再汇总：同时做，最后合并</text>
    <g font-size="14" fill="#f4ede4">
      <rect x="20" y="264" width="70" height="34" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="55" y="286">任务</text>
      <rect x="150" y="234" width="120" height="30" rx="8" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="210" y="254">子任务 A</text>
      <rect x="150" y="268" width="120" height="30" rx="8" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="210" y="288">子任务 B</text>
      <rect x="150" y="302" width="120" height="30" rx="8" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="210" y="322">子任务 C</text>
      <rect x="340" y="264" width="80" height="34" rx="10" fill="rgba(167,243,208,.16)" stroke="#a7f3d0"/>
      <text x="380" y="286">汇总</text>
    </g>
    <g stroke="#a7f3d0" stroke-width="2">
      <line x1="90" y1="276" x2="148" y2="250" marker-end="url(#ma-a2)"/>
      <line x1="90" y1="282" x2="148" y2="283" marker-end="url(#ma-a2)"/>
      <line x1="90" y1="288" x2="148" y2="316" marker-end="url(#ma-a2)"/>
      <line x1="270" y1="250" x2="338" y2="276" marker-end="url(#ma-a2)"/>
      <line x1="270" y1="283" x2="338" y2="282" marker-end="url(#ma-a2)"/>
      <line x1="270" y1="316" x2="338" y2="288" marker-end="url(#ma-a2)"/>
    </g>
    <text x="220" y="356" fill="#9a93a8" font-size="13">拆法事先定好，子任务之间互不依赖</text>

    <line x1="20" y1="374" x2="420" y2="374" stroke="rgba(255,255,255,.12)" stroke-dasharray="6 6"/>
    <text x="220" y="402" fill="#a7f3d0" font-size="16" font-weight="800">流水线：上一站的输出是下一站的输入</text>
    <g font-size="14" fill="#f4ede4">
      <rect x="20" y="416" width="78" height="32" rx="8" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="59" y="437">检索</text>
      <rect x="124" y="416" width="78" height="32" rx="8" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="163" y="437">提纲</text>
      <rect x="228" y="416" width="78" height="32" rx="8" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="267" y="437">撰写</text>
      <rect x="332" y="416" width="88" height="32" rx="8" fill="rgba(167,243,208,.16)" stroke="#a7f3d0"/>
      <text x="376" y="437">校对</text>
    </g>
    <g stroke="#a7f3d0" stroke-width="2">
      <line x1="98" y1="432" x2="122" y2="432" marker-end="url(#ma-a2)"/>
      <line x1="202" y1="432" x2="226" y2="432" marker-end="url(#ma-a2)"/>
      <line x1="306" y1="432" x2="330" y2="432" marker-end="url(#ma-a2)"/>
    </g>
  </g>
</svg>
<figcaption>三种「分工」型拓扑：动态拆分、固定并行、固定顺序</figcaption>
</figure>

多 Agent 系统的形状有很多，常见的是下面五种。前三种解决「活太多，一个人干不过来」，后两种解决「一个人干，质量或分工有问题」。

### 1. 主管-工人（orchestrator / subagent）

一个**主 Agent**（主管、orchestrator）理解任务、制定计划，把任务拆成若干子任务，派给**子 Agent**（工人、subagent）去做；子 Agent 做完后把结论交回，主 Agent 汇总，必要时再派下一轮。

关键在于**拆分是动态的**：拆几份、每份做什么，由主 Agent 在运行时根据任务决定，事先写不死。Anthropic 的调研系统就是这种结构：主 Agent 分析问题、制定研究计划，同时启动多个子 Agent，每个子 Agent 负责一个方向，自己搜索、判断、再搜索，最后返回精简的发现。

编程 Agent 里也很常见。Claude Code 的子 Agent 就是这种模式：主对话可以把「在整个代码库里找出所有调用这个接口的地方」这样的任务交给子 Agent，子 Agent 在自己的窗口里翻遍文件，只把结论交回主对话。

在 OpenAI Agents SDK 里，这种模式对应 **agents as tools**：主管 Agent 通过 `Agent.as_tool()` 把子 Agent 包装成工具来调用，主管始终掌握对话的控制权。

### 2. 并行扇出再汇总（fan-out / fan-in）

把任务按固定的方式切成几份，同时交给几个 Agent（或几次模型调用）处理，最后由一个汇总步骤合并。它和主管-工人的区别在于：**拆法是事先定好的**，通常由代码完成，而不是由模型临时决定。

Anthropic 把这种并行分成两种：

- **分段**（sectioning）：把任务切成互不依赖的几块，比如一个 Agent 回答用户问题，另一个 Agent 同时检查内容是否合规；
- **投票**（voting）：同一个任务跑多次，取多数结果或综合多个视角，比如让几个 Agent 分别从不同角度检查代码有没有安全漏洞。

这就是大家熟悉的 map-reduce 思路，后端工程师应该不陌生。

### 3. 流水线（pipeline）

任务按固定顺序分成几个阶段，上一个阶段的输出是下一个阶段的输入：检索 → 写提纲 → 撰写 → 校对。每个阶段可以是一个专门的 Agent，有自己的提示词和工具。

流水线的好处是每一站都很简单，而且站与站之间可以加**检查关口**：提纲不合格就不往下走。代价是**慢**（完全串行）和**脆**（前一站的错误会一路传下去）。Anthropic 把它叫作 prompt chaining（提示词链），适合能干净地拆成固定步骤的任务。

严格说，流水线不太需要「多 Agent」这个词，它更像普通的工作流。但很多框架里，流水线的每一站都被实现成一个 Agent，所以放在这里一起讲。

<figure>
<svg viewBox="0 0 440 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="生成者与评审者循环，以及交接">
  <rect width="440" height="400" fill="#0f0e1c"/>
  <defs>
    <marker id="ma-a3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#a7f3d0"/></marker>
    <marker id="ma-a4" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#ffd38a"/></marker>
  </defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="30" fill="#a7f3d0" font-size="16" font-weight="800">生成者 + 评审者：循环直到通过</text>
    <rect x="30" y="50" width="140" height="62" rx="12" fill="rgba(167,243,208,.14)" stroke="#a7f3d0"/>
    <text x="100" y="76" fill="#f4ede4" font-size="15" font-weight="800">生成者</text>
    <text x="100" y="98" fill="#9a93a8" font-size="13">写草稿、按意见改</text>
    <rect x="270" y="50" width="140" height="62" rx="12" fill="rgba(255,211,138,.12)" stroke="#ffd38a"/>
    <text x="340" y="76" fill="#f4ede4" font-size="15" font-weight="800">评审者</text>
    <text x="340" y="98" fill="#9a93a8" font-size="13">只看草稿和清单</text>
    <line x1="172" y1="66" x2="268" y2="66" stroke="#a7f3d0" stroke-width="2" marker-end="url(#ma-a3)"/>
    <text x="220" y="58" fill="#a7f3d0" font-size="13">草稿</text>
    <line x1="268" y1="98" x2="172" y2="98" stroke="#ffd38a" stroke-width="2" stroke-dasharray="5 4" marker-end="url(#ma-a4)"/>
    <text x="220" y="118" fill="#ffd38a" font-size="13">意见</text>
    <line x1="340" y1="112" x2="340" y2="138" stroke="#a7f3d0" stroke-width="2" marker-end="url(#ma-a3)"/>
    <rect x="270" y="140" width="140" height="32" rx="8" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="340" y="161" fill="#f4ede4" font-size="13">通过 → 交付</text>
    <text x="100" y="152" fill="#9a93a8" font-size="13">设轮数上限</text>
    <text x="100" y="170" fill="#9a93a8" font-size="13">超过就交给人</text>

    <line x1="20" y1="192" x2="420" y2="192" stroke="rgba(255,255,255,.12)" stroke-dasharray="6 6"/>
    <text x="220" y="222" fill="#a7f3d0" font-size="16" font-weight="800">交接（handoff）：把对话整个交出去</text>
    <g font-size="14" fill="#f4ede4">
      <rect x="20" y="262" width="70" height="36" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="55" y="285">用户</text>
      <rect x="122" y="262" width="110" height="36" rx="10" fill="rgba(167,243,208,.14)" stroke="#a7f3d0"/>
      <text x="177" y="285">分诊 Agent</text>
      <rect x="282" y="240" width="138" height="34" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="351" y="262">退款 Agent</text>
      <rect x="282" y="288" width="138" height="34" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="351" y="310">技术支持 Agent</text>
    </g>
    <line x1="90" y1="280" x2="120" y2="280" stroke="#a7f3d0" stroke-width="2" marker-end="url(#ma-a3)"/>
    <line x1="232" y1="274" x2="280" y2="258" stroke="#a7f3d0" stroke-width="2" marker-end="url(#ma-a3)"/>
    <line x1="232" y1="286" x2="280" y2="304" stroke="#9a93a8" stroke-width="1.5" stroke-dasharray="4 4" marker-end="url(#ma-a3)"/>
    <text x="220" y="350" fill="#f4ede4" font-size="13">对模型来说，交接就是调用一个工具，如 transfer_to_refund_agent</text>
    <text x="220" y="374" fill="#9a93a8" font-size="13">接手的 Agent 直接继续对话，分诊 Agent 不再回收结果</text>
  </g>
</svg>
<figcaption>两种「协作」型拓扑：一个负责挑错，一个负责转交</figcaption>
</figure>

### 4. 辩论与评审（生成者 + 评审者）

一个 Agent 负责生成，另一个 Agent 负责评审，评审意见再交回生成者修改，循环直到通过或者达到轮数上限。Anthropic 把它叫作 **evaluator-optimizer**（评估者-优化者），适合「评价标准清楚、迭代修改确实能提高质量」的任务，比如翻译、写代码、写一份需要满足很多要求的文档。

它为什么比「自己写完自己检查」有效？核心还是**上下文隔离**：评审者没有看到生成过程中的推理，不会被同一条思路带偏，只能根据产物本身和评审标准来判断。Cognition 在 2026 年的后续文章里提到，他们的代码评审 Agent 和写代码的 Agent 事先**不共享任何上下文**，评审者只看 diff，自己去发现需要的信息，效果反而更好。

再往前走一步是**多 Agent 辩论**：几个 Agent 各自给出答案和推理，互相阅读、反驳、修正，几轮之后收敛到一个答案。2023 年的一篇论文（Du et al.，Improving Factuality and Reasoning in Language Models through Multiagent Debate）报告，这种做法在数学、策略推理和事实准确性上有提升。辩论更像是「投票」的增强版，成本也高得多。

### 5. 去中心化交接（handoff）

前面几种都有一个「中心」：主管、汇总者或者固定的流程。**交接**不一样：当前的 Agent 判断「这件事该由别人处理」，就把**整个对话**交给另一个 Agent，由它直接继续和用户对话。

典型场景是客服：一个**分诊 Agent** 先了解用户的问题，然后交给退款 Agent、技术支持 Agent 或者账户 Agent。每个专门的 Agent 只需要自己领域的提示词和工具。

OpenAI Agents SDK 把这个概念做成了一等公民。几个值得了解的设计：

- **交接对模型来说就是一个工具**。默认的工具名是 `transfer_to_<agent_name>`，比如名为 Refund Agent 的 Agent 对应 `transfer_to_refund_agent`。模型「调用」这个工具，就完成了交接；
- **默认情况下，接手的 Agent 能看到之前的完整对话**。可以用 `input_filter` 过滤历史，比如去掉之前的工具调用记录；
- 可以用 `on_handoff` 回调在交接发生时做一些事（比如预先加载用户数据），用 `input_type` 让模型在交接时附带结构化信息（比如原因、优先级）。

交接和 agents as tools 的区别，在于**控制权在谁手里**：

| | agents as tools（主管-工人） | handoff（交接） |
|---|---|---|
| 控制权 | 主管始终掌握，子 Agent 做完就返回 | 交给接手者，由它负责之后的对话 |
| 子 Agent 看到什么 | 主管写给它的任务描述 | 默认是完整的对话历史 |
| 结果去向 | 回到主管，由主管汇总 | 直接回复用户 |
| 适合 | 有边界的子任务：查资料、算数据、审稿 | 按领域分流：客服、多业务入口 |

### 还有一种：群聊

还有一类设计是让一群 Agent 在一个「聊天室」里自由交流，谁想说话就说话，没有固定结构。这类设计很吸引眼球，但目前在生产中很少见。Cognition 在 2026 年的文章里直接说，任意结构的 Agent 网络「大多是一种分心」。本文不展开。

### 五种拓扑对照

| 拓扑 | 谁决定分工 | 并行 | 典型用途 | 主要风险 |
|---|---|---|---|---|
| 主管-工人 | 主 Agent（运行时） | 是 | 开放式调研、大范围代码搜索 | 拆分不当、派单含糊、成本失控 |
| 并行扇出 | 代码（设计时） | 是 | 多角度检查、批量处理、投票 | 汇总时冲突、重复劳动 |
| 流水线 | 代码（设计时） | 否 | 固定步骤的内容生产 | 慢、错误逐级传递 |
| 生成者 + 评审者 | 代码定循环，模型定内容 | 否 | 翻译、写代码、写文档 | 循环不收敛、评审标准模糊 |
| 交接 | 当前 Agent | 否 | 客服分流、多业务入口 | 交接错人、来回踢皮球、历史太长 |

## 子 Agent 真正的价值：隔离与并行

<figure>
<svg viewBox="0 0 440 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="一份合格的派单">
  <rect width="440" height="340" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif">
    <text x="220" y="30" fill="#a7f3d0" font-size="17" font-weight="800" text-anchor="middle">一份合格的派单</text>
    <rect x="20" y="46" width="400" height="226" rx="12" fill="rgba(255,255,255,.04)" stroke="#9a93a8"/>
    <g font-size="14" font-weight="700" text-anchor="middle">
      <rect x="36" y="62" width="84" height="32" rx="8" fill="rgba(167,243,208,.18)" stroke="#a7f3d0"/>
      <text x="78" y="83" fill="#a7f3d0">目标</text>
      <rect x="36" y="114" width="84" height="32" rx="8" fill="rgba(167,243,208,.18)" stroke="#a7f3d0"/>
      <text x="78" y="135" fill="#a7f3d0">边界</text>
      <rect x="36" y="166" width="84" height="32" rx="8" fill="rgba(167,243,208,.18)" stroke="#a7f3d0"/>
      <text x="78" y="187" fill="#a7f3d0">输出格式</text>
      <rect x="36" y="218" width="84" height="32" rx="8" fill="rgba(167,243,208,.18)" stroke="#a7f3d0"/>
      <text x="78" y="239" fill="#a7f3d0">停止条件</text>
    </g>
    <g font-size="14" fill="#f4ede4">
      <text x="136" y="83">要回答什么问题，结果给谁用</text>
      <text x="136" y="135">不做什么，和别的子 Agent 怎么分</text>
      <text x="136" y="187">结构、长度上限、必须附来源</text>
      <text x="136" y="239">读够多少、花多少、何时放弃</text>
    </g>
    <text x="220" y="300" fill="#9a93a8" font-size="13" text-anchor="middle">可选：建议的工具与来源、已知事实、共享的约定</text>
    <text x="220" y="326" fill="#fca5a5" font-size="14" text-anchor="middle">缺一项，就要靠子 Agent 自己猜</text>
  </g>
</svg>
<figcaption>子 Agent 看不到主 Agent 的上下文，派单就是它对任务的全部了解</figcaption>
</figure>

为什么主管-工人模式在调研任务上效果好？可以从三个角度理解。

### 1. 上下文隔离：每个窗口只装一件事

本系列《上下文工程》把管理上下文的手段归纳为写入、选择、压缩、隔离四种。子 Agent 就是最彻底的**隔离**：

- 每个子 Agent 有**自己独立的上下文窗口**，可以放开去搜索、读网页、试错；
- 做完之后只把**精简的结论**交回主 Agent。子 Agent 可能读了几万 token 的原文，返回的往往只有几百到一两千 token；
- 主 Agent 的窗口里只有目标、计划和各个子任务的结论，不会被几十页网页原文淹没。

换个角度看，子 Agent 其实是一个**带推理能力的压缩器**：它把大量原始信息读完、筛选、提炼，交出一份摘要。这比在单 Agent 里用一次摘要调用去压缩历史更可控，因为子 Agent 从一开始就知道「我读这些是为了回答什么问题」。

Claude Code 的文档对子 Agent 的描述也是这个意思：每个子 Agent 在自己的上下文窗口里运行，有自定义的系统提示词、独立的工具权限，完成后只把结果返回给主对话，搜索结果、日志、文件内容这些冗长的东西都留在子 Agent 里。

### 2. 并行：把等待的时间重叠起来

几个子 Agent 互不依赖，就可以同时跑。Anthropic 的系统里有两层并行：主 Agent 同时启动 3～5 个子 Agent，每个子 Agent 又同时调用 3 个以上的工具。他们报告，这让复杂问题的调研时间**最多缩短了 90%**。

这和后端里用线程池并发调用多个下游服务是一个道理：总耗时从「各部分相加」变成「最慢的那部分」。

### 3. 专精：不同的提示词、工具和模型

每个子 Agent 只做一类事，系统提示词可以短而专注，工具列表可以只给它需要的几个（比如只读工具），甚至可以**用不同的模型**。Anthropic 的调研系统用较强的模型（Claude Opus 4）当主 Agent，用更快、更便宜的模型（Claude Sonnet 4）当子 Agent。

### 一个更本质的解释：花够 token

Anthropic 的文章里有一个很有意思的分析。他们在 BrowseComp（一个考察 Agent 查找难找信息能力的评测）上发现，**仅 token 用量一项就能解释 80% 的表现差异**，加上工具调用次数和模型选择，三个因素能解释 95%。

他们的结论是：多 Agent 系统之所以有效，主要是因为它**帮助系统花掉了足够多的 token** 去解决问题。单个 Agent 的窗口有限，花不了那么多；拆成多个窗口并行，总的「思考量」和「阅读量」就上去了。

这个解释也直接指出了代价：效果提升是用 token 换来的。后面会专门讲。

## 派单：怎么给子 Agent 布置任务

主管-工人模式里，最容易被低估的一环是**派单**：主 Agent 写给子 Agent 的那段任务描述。

子 Agent 看不到主 Agent 的上下文。用户之前说过什么、主 Agent 已经知道什么、其他子 Agent 在做什么，它一概不知。**派单就是它对这个任务的全部了解**。派单写得含糊，子 Agent 只能猜。

### 一个反面例子

Anthropic 在文章里讲过他们早期踩的坑：主 Agent 给子 Agent 的指令很短，比如「研究一下半导体短缺」。结果子 Agent 经常误解任务，或者几个子 Agent 做了重复的搜索。有一次，一个子 Agent 去查了 2021 年的汽车芯片危机，另外两个子 Agent 却重复地研究 2025 年的供应链现状，彼此没有分工。

### 派单的四个要素

Anthropic 总结，每个子 Agent 需要拿到：**目标**、**输出格式**、**该用哪些工具和来源的指导**、**清晰的任务边界**。结合实践，可以整理成下面这张表：

| 要素 | 要写清楚什么 | 缺了会怎样 |
|---|---|---|
| 目标 | 要回答的具体问题；结果拿去做什么 | 子 Agent 按自己的理解发挥，答非所问 |
| 边界 | 只做哪部分、明确不做什么；和其他子 Agent 的分工 | 重复劳动，或者越界去做别人的事 |
| 输出格式 | 结构（如 JSON 字段）、长度上限、是否要附来源和可信度 | 返回一大段原文，主 Agent 的窗口又被塞满 |
| 停止条件 | 读够多少来源、最多调用多少次工具、找不到时怎么办 | 没完没了地搜索，或者过早收工 |
| 工具与来源（可选） | 建议用哪些工具、优先哪类来源 | 用错工具，比如在网上搜只存在于内部系统的信息 |
| 共享的约定（可选） | 已经确定的事实、命名、口径 | 子 Agent 自己做出与全局不一致的决定 |

「停止条件」值得单独强调。Anthropic 列出的早期问题里，有好几条都和停不下来有关：为一个简单问题启动了 50 个子 Agent；为了找不存在的资料无休止地搜索；已经拿到足够的结果还继续做。

写成模板大概是这样：

```text
目标：对比 A、B、C 三款向量库在千万级数据下的查询延迟和内存占用，结果用于选型报告的「性能」一节
边界：只看性能；价格和生态由其他子 Agent 负责，不要涉及
输出格式：JSON 列表，不超过 5 条结论，每条附来源链接和可信度（高/中/低）
停止条件：读够 4 个可靠来源，或连续两次搜索没有新信息就停；最多 15 次工具调用
建议：优先官方文档和公开压测报告，其次技术博客；避免内容农场
已知：部署环境不允许使用外部托管服务
```

### 按任务复杂度决定投入

派几个子 Agent、每个做多少，也需要明确告诉主 Agent。Anthropic 在主 Agent 的提示词里写进了这样的规则：

| 任务类型 | 子 Agent 数量 | 每个的工具调用 |
|---|---|---|
| 简单的事实查找 | 1 个 | 3～10 次 |
| 直接对比 | 2～4 个 | 每个 10～15 次 |
| 复杂研究 | 10 个以上，职责划分清楚 | 视情况 |

没有这样的规则，模型很难自己判断「这个问题值得花多少力气」，要么杀鸡用牛刀，要么浅尝辄止。

他们还总结了几条写提示词的原则，比如「**像你的 Agent 一样思考**」（在模拟环境里一步步看 Agent 的行为，找出它在哪里犯错）、「**教主 Agent 怎么派活**」、「**先宽后窄**」（先用短而宽泛的查询了解全貌，再逐步聚焦），都很实用。

### 过度指挥也是问题

派单也不是越细越好。Cognition 在 2026 年 4 月的文章《Multi-Agents: What's Actually Working》里提到，他们的主管 Agent 往往**过度规定**子 Agent 的做法，而子 Agent 又常常**错误地以为**自己和主管共享某些状态。

所以派单要把「做什么、交付什么」写清楚，把「怎么做」留给子 Agent；同时**明确说出哪些信息是共享的**，不要让子 Agent 自己假设。

## 结果汇总与冲突处理

子 Agent 交回结论之后，主 Agent 要把它们合成一份结果。这一步比看上去难。

### 统一格式，方便合并

如果每个子 Agent 都按同样的结构返回（结论、来源、可信度），汇总就可以部分用代码完成：去重、按主题分组、按可信度排序。返回自由文本的话，汇总只能完全交给模型，出错的概率更高。

### 去重

几个子 Agent 各自独立工作，难免读到同样的资料、得出同样的结论。下文的演示里，一篇「综述」被三个子 Agent 各读了一次，汇总时要合并成一条。这也是多 Agent 的一种浪费：单 Agent 读过的东西它自己知道，子 Agent 之间却互相不知道。

### 冲突的两种类型

| 类型 | 例子 | 处理方式 |
|---|---|---|
| 事实冲突 | 两个子 Agent 找到的资料对同一个数字说法不同 | 保留双方说法和来源；按来源可信度取舍；或者再派一个子 Agent 专门核实 |
| 决策冲突 | 两个子 Agent 各自定了不同的命名、风格、接口 | 很难事后合并，应该**事前避免** |

事实冲突是正常的，甚至是有价值的：它告诉你这个问题有争议。真正麻烦的是决策冲突。

Cognition 的 Flappy Bird 例子讲的就是这个：把「做一个 Flappy Bird 小游戏」拆成「做背景和水管」和「做小鸟」两个子任务，一个子 Agent 做出了超级马里奥风格的背景，另一个做出的小鸟既不像原版、动起来也不对，最后负责合并的 Agent 面对两份风格完全不搭的产物。他们由此提出两条原则：

1. **共享上下文，而且要共享完整的 Agent 轨迹，而不只是单条消息**；
2. **每个动作都隐含着决定，相互冲突的决定会带来糟糕的结果**。

### 让写操作保持单线程

一年之后，Cognition 在后续文章里给出了一个更具体的结论：多 Agent 系统在**写操作保持单线程**、**额外的 Agent 贡献的是智力而不是动作**时效果最好。

翻译成工程语言：

- 只有一个 Agent 负责修改最终产物（写代码、写报告、改数据）；
- 其他 Agent 负责查资料、给建议、做评审，它们的输出是**信息**，由那个唯一的写者决定怎么用。

这和数据库里的「单写者」原则很像：多个线程并发写同一份数据，就要加锁、处理冲突；只有一个写者，问题就简单得多。

### 汇总本身也要检查

汇总是一次新的模型调用，也会出错：漏掉某个子 Agent 的关键结论、把 A 的结论张冠李戴到 B 上、编造出没有来源支持的总结。几个常见的防护：

- **引用核查**：Anthropic 的系统在最后有一个专门的 CitationAgent，负责处理文档和报告，确定每条结论该引用哪个来源；
- **结果落盘，传引用**：Anthropic 提到，让子 Agent 把产出写到外部存储里，只把轻量的引用交回主 Agent，可以减少层层转述造成的信息失真（他们称之为「传话游戏」）；
- **主 Agent 的计划也落盘**：Anthropic 的主 Agent 会把研究计划存进记忆，因为上下文超过 20 万 token 时会被截断，计划不能只放在窗口里。

## 动手：一个并行调研的 orchestrator

下面用 Python 标准库实现一个最小的主管-工人系统，把前面讲的东西串起来：

- 主 Agent 把「给客服问答系统选向量库」拆成性能、成本、生态 3 个子任务，每个子任务的派单都包含目标、边界、输出格式和停止条件；
- 3 个子 Agent 各有**独立的上下文**和自己的工具（搜索、读网页），用 `ThreadPoolExecutor` 并行运行；
- 子 Agent 只返回精简结论，主 Agent 汇总时去重、按产品分组；
- 作为对照，再让**一个 Agent** 在一个上下文里完成全部工作；
- 统计每个 Agent 每次调用模型时的上下文大小（粗估 token）、累计输入 token，以及单 Agent、多 Agent 串行、多 Agent 并行三种方式的耗时。

这里没有接真实的大模型，**用一个假模型代替真实 LLM**：`fake_llm` 按固定规则读上下文、决定下一步（搜索、读网页还是交卷）。换成真实 API 只需替换 `fake_llm` 函数，让它把上下文发给模型并解析返回的工具调用。工具也是假的，用 `sleep` 模拟网络延迟；三款产品和其中的数据都是**虚构的**。

```python
"""主管-工人（orchestrator / subagent）多 Agent 演示：假模型 + 假工具，只用标准库。"""
import json, math, re, threading, time
from concurrent.futures import ThreadPoolExecutor

LLM_LATENCY, TOOL_LATENCY = 0.05, 0.2      # 用 sleep 模拟模型和工具的耗时（秒）

def est_tokens(text):
    """粗估 token：一个汉字算 1 个，其余字符每 4 个算 1 个。"""
    cjk = len(re.findall(r"[一-鿿]", text))
    return cjk + math.ceil((len(text) - cjk) / 4)

# ---------- 假资料库（产品和数据都是虚构的） ----------
FILLER = "（页面其余部分：安装步骤、配置截图、版本历史、评论区讨论……）" * 12
TOPICS = {
    "性能": [("/perf/a", "A：千万级向量下 P99 延迟最低，但索引全部常驻内存"),
             ("/perf/b", "B：支持磁盘索引，内存约为 A 的三分之一，延迟略高"),
             ("/perf/c", "C：单机上限较低，过亿规模需要分片")],
    "成本": [("/cost/a", "A：只有托管版，按向量数和查询量计费"),
             ("/cost/b", "B：开源可自建，备份和扩容要自己做"),
             ("/cost/c", "C：作为现有数据库的插件运行，不增加新组件")],
    "生态": [("/eco/a", "A：主流 Agent 框架都有现成集成"),
             ("/eco/b", "B：官方 SDK 覆盖 Python、Go、Java"),
             ("/eco/c", "C：直接写 SQL，能和业务表联合过滤")],
}
OVERVIEW = ("/overview", "综述：三款都能满足中等规模，差异主要在部署方式和成本")
PAGES = {url: f"要点：{p}\n{FILLER}" for url, p in [OVERVIEW] + [x for v in TOPICS.values() for x in v]}

# ---------- 假工具 ----------
def web_search(query):
    time.sleep(TOOL_LATENCY)
    hits = [OVERVIEW] + next(v for k, v in TOPICS.items() if k in query)
    return "\n".join(f"链接：{u}  摘要：{p[:10]}…" for u, p in hits)

def fetch(url):
    time.sleep(TOOL_LATENCY)
    return PAGES[url]

TOOLS = {"web_search": web_search, "fetch": fetch}

# ---------- 假模型：按规则读上下文、决定下一步。换成真实 LLM 只需替换这个函数 ----------
def fake_llm(context):
    time.sleep(LLM_LATENCY)
    role = re.search(r"角色：(\w+)", context).group(1)
    if role == "planner":                                    # 主 Agent 拆任务
        return {"type": "final", "content": [
            {"目标": f"调研三款向量库的{t}", "查询词": [f"向量库 {t} 对比"],
             "边界": f"只看{t}，不评价其他维度", "输出": "JSON，不超过 5 条结论，附来源",
             "停止条件": "读够 4 页或没有新链接就停"} for t in TOPICS]}
    if role == "synth":                                      # 主 Agent 汇总
        merged = {}
        for p in re.findall(r'"([^"/：]{1,4}：[^"]+)"', context):
            group = merged.setdefault(p.split("：")[0], [])
            if p not in group:
                group.append(p)                              # 去重：综述被三个子 Agent 各读了一次
        return {"type": "final", "content": merged}
    # 工人（子 Agent 或单 Agent）：先搜，再读，最后总结
    queries = re.findall(r"查询词：(.+)", context)[0].split("；")
    limit = int(re.search(r"最多读取：(\d+)", context).group(1))
    searched = re.findall(r"→ web_search\((.+)\)", context)
    fetched = re.findall(r"→ fetch\((.+)\)", context)
    for q in queries:
        if q not in searched:
            return {"type": "tool", "tool": "web_search", "arg": q}
    links = [u for u in dict.fromkeys(re.findall(r"链接：(\S+)", context)) if u not in fetched]
    if links and len(fetched) < limit:
        return {"type": "tool", "tool": "fetch", "arg": links[0]}
    points = list(dict.fromkeys(re.findall(r"要点：(.+)", context)))
    return {"type": "final", "content": {"结论": points, "来源": fetched}}

# ---------- 记录每次模型调用：谁、输入多少 token、输出多少 token ----------
class Tracer:
    def __init__(self):
        self.rows, self.lock = [], threading.Lock()
    def log(self, agent, ctx_tok, out_tok):
        with self.lock:
            self.rows.append((agent, ctx_tok, out_tok))
    def stats(self, prefix=""):
        rows = [r for r in self.rows if r[0].startswith(prefix)]
        return {"calls": len(rows), "input": sum(r[1] for r in rows),
                "output": sum(r[2] for r in rows), "peak": max(r[1] for r in rows)}

def run_agent(name, system, task, tracer):
    """一个最小的 Agent 循环：每一步把整段上下文交给模型，执行工具，把结果追加回去。"""
    messages = [system, task]
    while True:
        ctx = "\n".join(messages)
        action = fake_llm(ctx)
        out = json.dumps(action, ensure_ascii=False)
        tracer.log(name, est_tokens(ctx), est_tokens(out))
        if action["type"] == "final":
            return action["content"]
        messages += [f"→ {action['tool']}({action['arg']})", TOOLS[action["tool"]](action["arg"])]

WORKER_SYS = "角色：worker\n你是调研助手。工具：web_search(query)、fetch(url)。" + "工具说明与注意事项……" * 20

def brief_to_text(b):
    return (f"任务目标：{b['目标']}\n查询词：{'；'.join(b['查询词'])}\n边界：{b['边界']}\n"
            f"输出格式：{b['输出']}\n停止条件：{b['停止条件']}\n最多读取：4 页")

def orchestrate(parallel, tracer):
    plan = run_agent("lead/plan", "角色：planner", "调研：给客服问答系统选向量库（A/B/C）", tracer)
    jobs = [(f"sub{i + 1}", WORKER_SYS, brief_to_text(b)) for i, b in enumerate(plan)]
    if parallel:
        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            results = list(pool.map(lambda j: run_agent(*j, tracer), jobs))
    else:
        results = [run_agent(*j, tracer) for j in jobs]
    # 主 Agent 只看到每个子 Agent 的精简结论，看不到它们读过的整页内容
    summary = "\n".join(json.dumps(r, ensure_ascii=False) for r in results)
    return run_agent("lead/synth", "角色：synth", summary, tracer), results

def single_agent(tracer):
    task = ("任务目标：调研三款向量库的性能、成本、生态\n"
            "查询词：向量库 性能 对比；向量库 成本 对比；向量库 生态 对比\n最多读取：10 页")
    return run_agent("single", WORKER_SYS, task, tracer)

if __name__ == "__main__":
    t0 = time.perf_counter(); tr_single = Tracer(); single_agent(tr_single)
    t_single = time.perf_counter() - t0
    t0 = time.perf_counter(); orchestrate(False, Tracer()); t_serial = time.perf_counter() - t0
    t0 = time.perf_counter(); tr = Tracer(); report, results = orchestrate(True, tr)
    t_par = time.perf_counter() - t0

    print("== 子 Agent 返回给主 Agent 的内容（精简结论）")
    for i, r in enumerate(results, 1):
        print(f"sub{i}:", json.dumps(r, ensure_ascii=False))
    print("\n== 主 Agent 汇总（按产品分组、去重）")
    for k, v in report.items():
        print(k, "→", "；".join(v))

    print("\n== 各 Agent 的上下文（token 粗估）")
    print(f"{'Agent':<11}{'调用':>4}{'峰值上下文':>8}{'累计输入':>8}{'输出':>6}")
    for name in ["lead/plan", "sub1", "sub2", "sub3", "lead/synth"]:
        s = tr.stats(name)
        print(f"{name:<11}{s['calls']:>6}{s['peak']:>12}{s['input']:>12}{s['output']:>8}")
    m, s = tr.stats(), tr_single.stats()
    print(f"{'多Agent合计':<9}{m['calls']:>6}{m['peak']:>12}{m['input']:>12}{m['output']:>8}")
    print(f"{'单Agent':<10}{s['calls']:>6}{s['peak']:>12}{s['input']:>12}{s['output']:>8}")

    print("\n== 耗时（每次运行略有不同）")
    print(f"单 Agent：{t_single:.2f}s   多 Agent 串行：{t_serial:.2f}s   多 Agent 并行：{t_par:.2f}s")
```

运行输出（耗时每次运行略有不同）：

```text
== 子 Agent 返回给主 Agent 的内容（精简结论）
sub1: {"结论": ["综述：三款都能满足中等规模，差异主要在部署方式和成本", "A：千万级向量下 P99 延迟最低，但索引全部常驻内存", "B：支持磁盘索引，内存约为 A 的三分之一，延迟略高", "C：单机上限较低，过亿规模需要分片"], "来源": ["/overview", "/perf/a", "/perf/b", "/perf/c"]}
sub2: {"结论": ["综述：三款都能满足中等规模，差异主要在部署方式和成本", "A：只有托管版，按向量数和查询量计费", "B：开源可自建，备份和扩容要自己做", "C：作为现有数据库的插件运行，不增加新组件"], "来源": ["/overview", "/cost/a", "/cost/b", "/cost/c"]}
sub3: {"结论": ["综述：三款都能满足中等规模，差异主要在部署方式和成本", "A：主流 Agent 框架都有现成集成", "B：官方 SDK 覆盖 Python、Go、Java", "C：直接写 SQL，能和业务表联合过滤"], "来源": ["/overview", "/eco/a", "/eco/b", "/eco/c"]}

== 主 Agent 汇总（按产品分组、去重）
综述 → 综述：三款都能满足中等规模，差异主要在部署方式和成本
A → A：千万级向量下 P99 延迟最低，但索引全部常驻内存；A：只有托管版，按向量数和查询量计费；A：主流 Agent 框架都有现成集成
B → B：支持磁盘索引，内存约为 A 的三分之一，延迟略高；B：开源可自建，备份和扩容要自己做；B：官方 SDK 覆盖 Python、Go、Java
C → C：单机上限较低，过亿规模需要分片；C：作为现有数据库的插件运行，不增加新组件；C：直接写 SQL，能和业务表联合过滤

== 各 Agent 的上下文（token 粗估）
Agent        调用   峰值上下文    累计输入    输出
lead/plan       1          20          20     235
sub1            6        1669        5376     184
sub2            6        1664        5359     177
sub3            6        1638        5275     163
lead/synth      1         286         286     192
多Agent合计     20        1669       16316     951
单Agent        14        3707       24091     409

== 耗时（每次运行略有不同）
单 Agent：3.32s   多 Agent 串行：4.01s   多 Agent 并行：1.41s
```

逐项看这组数字：

**主 Agent 的窗口很干净。** 汇总时主 Agent 的输入只有约 290 token，因为它拿到的是三份精简结论，而不是十几页网页原文。规划和汇总两次调用加起来不到 600 token。

**单个窗口的峰值降了一半多。** 单 Agent 最后一次调用时，上下文里装着全部 10 页网页，约 3,700 token；每个子 Agent 的峰值只有约 1,660 token。演示里每页只有几百 token，真实网页动辄几千上万，差距会大得多，单 Agent 可能早就撞上窗口上限了。

**并行把时间压了下来。** 同样是 3 个子 Agent，串行跑要 4 秒，并行只要 1.4 秒左右，接近「最慢的那个子 Agent + 规划和汇总」。单 Agent 介于两者之间：它读的页数少（没有重复），但只能一步步来。

**累计 token 的结果可能出乎意料：这里多 Agent 反而更少。** 原因是单 Agent 的上下文在不断变长，每一步都要把之前读过的全部内容重新发给模型，累计输入大致随步数平方增长；子 Agent 的窗口短，这部分开销小。

但不要因此得出「多 Agent 更省钱」的结论，演示里刻意让两边做了**同样多的工作**。注意第三个细节：多 Agent 一共读了 12 页，比单 Agent 多 2 页，因为那篇综述被三个子 Agent 各读了一次，这就是**重复劳动**。真实系统里还有几个因素会把天平推向另一边：

- **多 Agent 通常被用来做更多的事**。正是因为窗口够用了，系统才会开更多子 Agent、读更多资料，这也是它效果好的原因（前面说的「花够 token」）；
- **每个子 Agent 都要重复携带系统提示词和工具定义**，真实系统里这部分可能有几千 token；
- **提示词缓存**会大幅降低单 Agent 重复发送相同前缀的成本（缓存命中的部分按较低价格计费），这部分优势多 Agent 吃不到那么多，因为每个子 Agent 的上下文都是新的。

所以 Anthropic 给出的真实数字是：Agent 消耗的 token 大约是普通对话的 4 倍，多 Agent 系统大约是 **15 倍**。

> 想把 `fake_llm` 换成真实模型，最小的改动是：把 `messages` 组织成 API 要求的格式，把 `web_search`、`fetch` 声明成工具（见本系列《Function Calling 与 MCP》），再从返回结果里取出工具调用。异步版本可以用 `asyncio.gather` 代替线程池，思路完全一样。

## 动手：生成者 + 评审者循环

第二个演示是生成者 + 评审者循环。为了呼应前面的内容，让生成者写的正是一份**子 Agent 派单**，评审者按「目标、边界、输出格式、停止条件」四项清单检查。

注意两个设计：

- **评审者每一轮都是全新的上下文**，只看到清单和当前草稿，看不到生成者的历史，也看不到上一轮的意见；
- **生成者的上下文会累积**：每一轮都会追加上一版草稿和评审意见；
- 循环有**轮数上限**，超过就交给人。

生成者和评审者同样是**假模型**（`fake_generator`、`fake_critic`），换成真实 LLM 只需替换这两个函数。为了模拟真实模型常见的「改了这里、坏了那里」，假生成者在第二轮会把长度上限弄丢。

```python
"""生成者 + 评审者循环：生成者写一份子任务派单，评审者按清单打回，直到通过或达到轮数上限。"""
import json, math, re

def est_tokens(text):
    cjk = len(re.findall(r"[一-鿿]", text))
    return cjk + math.ceil((len(text) - cjk) / 4)

RUBRIC = {   # 评审清单：每一项都是可以机械检查的规则
    "目标": "写明要回答什么问题",
    "边界": "写明不做什么，避免和其他子 Agent 重复",
    "输出格式": "规定格式和长度上限（含「不超过」）",
    "停止条件": "写明什么时候停",
}

# 假生成者：根据评审意见补全字段。换成真实 LLM 只需替换这个函数
FIXES = {
    "目标": "目标：对比 A、B、C 三款向量库在千万级数据下的查询延迟和内存占用",
    "边界": "边界：只看性能，不评价价格和生态（由其他子 Agent 负责）",
    "输出格式": "输出格式：JSON 列表，不超过 5 条结论，每条附来源链接",
    "停止条件": "停止条件：读够 4 个来源，或连续两次搜索没有新信息就停",
}
def fake_generator(context):
    draft = ["调研一下向量数据库的性能。"]
    for field in RUBRIC:
        if f"缺少「{field}」" in context:
            draft.append(FIXES[field])
    if "缺少「目标」" in context:
        draft = draft[1:]                     # 有了明确目标，就删掉最初那句含糊的话
    # 模拟真实模型的「顺手改坏」：第二轮修改时把长度上限写丢了
    if context.count("评审意见") == 1 and "缺少「输出格式」" in context:
        draft = [d.replace("不超过 5 条结论，", "") for d in draft]
    return "\n".join(draft)

# 假评审者：只看草稿和清单，不看生成者的历史
def fake_critic(context):
    draft = context.split("【草稿】")[1]
    issues = []
    for field, rule in RUBRIC.items():
        if f"{field}：" not in draft or (field == "输出格式" and "不超过" not in draft):
            issues.append(f"缺少「{field}」：{rule}")
    return {"pass": not issues, "issues": issues}

def loop(task, max_rounds=4):
    gen_ctx = f"任务：{task}"
    for rnd in range(1, max_rounds + 1):
        draft = fake_generator(gen_ctx)
        critic_ctx = "清单：" + json.dumps(RUBRIC, ensure_ascii=False) + "\n【草稿】" + draft
        verdict = fake_critic(critic_ctx)
        print(f"--- 第 {rnd} 轮  生成者输入 {est_tokens(gen_ctx)} tok，评审者输入 {est_tokens(critic_ctx)} tok")
        print(draft)
        print("评审：", "通过" if verdict["pass"] else "打回")
        for i in verdict["issues"]:
            print("  -", i)
        if verdict["pass"]:
            return draft
        # 把草稿和评审意见追加到生成者的上下文，进入下一轮
        gen_ctx += f"\n上一版：{draft}\n评审意见：" + "；".join(verdict["issues"])
    print("达到轮数上限，交给人处理")
    return None

if __name__ == "__main__":
    loop("给「性能」子 Agent 写一份派单")
```

运行输出：

```text
--- 第 1 轮  生成者输入 14 tok，评审者输入 84 tok
调研一下向量数据库的性能。
评审： 打回
  - 缺少「目标」：写明要回答什么问题
  - 缺少「边界」：写明不做什么，避免和其他子 Agent 重复
  - 缺少「输出格式」：规定格式和长度上限（含「不超过」）
  - 缺少「停止条件」：写明什么时候停
--- 第 2 轮  生成者输入 104 tok，评审者输入 162 tok
目标：对比 A、B、C 三款向量库在千万级数据下的查询延迟和内存占用
边界：只看性能，不评价价格和生态（由其他子 Agent 负责）
输出格式：JSON 列表，每条附来源链接
停止条件：读够 4 个来源，或连续两次搜索没有新信息就停
评审： 打回
  - 缺少「输出格式」：规定格式和长度上限（含「不超过」）
--- 第 3 轮  生成者输入 223 tok，评审者输入 169 tok
目标：对比 A、B、C 三款向量库在千万级数据下的查询延迟和内存占用
边界：只看性能，不评价价格和生态（由其他子 Agent 负责）
输出格式：JSON 列表，不超过 5 条结论，每条附来源链接
停止条件：读够 4 个来源，或连续两次搜索没有新信息就停
评审： 通过
```

三轮才通过：第一轮的派单只有一句「调研一下」，四项全缺；第二轮补齐了，却丢了长度上限；第三轮才完整。

几个观察：

- **评审者的输入几乎不变**（84 → 162 → 169 token），它只看当前草稿，增长的部分来自草稿本身变长。生成者的输入则随轮数增长（14 → 104 → 223），因为它要带着历史修改；
- **评审标准要能检查**。这里的清单是机械规则，所以评审结果稳定。真实场景里评审者是模型，标准越模糊，评审越像掷骰子，循环就越难收敛；
- **评审者会抓到「回归」**。第二轮的修改顺手弄坏了一项，评审者照样打回。这正是独立评审的价值：它不知道「这一轮只是在补漏」，所以会把所有项重新查一遍。

## 参考写法：框架里的子 Agent 与交接

下面两段是真实框架的**参考写法**，依赖外部账号和 API Key，本文没有实际运行，接口以官方文档为准。

**OpenAI Agents SDK 的交接与 agents as tools：**

```python
from agents import Agent, Runner

refund_agent = Agent(name="Refund Agent", instructions="处理退款：核对订单，说明退款规则。")
tech_agent = Agent(name="Tech Support Agent", instructions="处理播放、登录等技术问题。")

# 交接：对模型来说是两个工具 transfer_to_refund_agent、transfer_to_tech_support_agent
triage = Agent(
    name="Triage Agent",
    instructions="判断用户的问题属于哪一类，交给对应的 Agent。",
    handoffs=[refund_agent, tech_agent],
)
result = Runner.run_sync(triage, "上周开的会员想退款")
print(result.final_output)

# agents as tools：主管调用子 Agent，拿回结果后自己继续回答
manager = Agent(
    name="Manager",
    instructions="回答用户问题，需要时咨询退款规则。",
    tools=[refund_agent.as_tool(tool_name="ask_refund_policy", tool_description="查询退款规则")],
)
```

**Claude Code 的子 Agent 定义**（放在项目的 `.claude/agents/` 目录下，正文就是子 Agent 的系统提示词；`tools` 限定它能用的工具，这里只给只读工具）：

```markdown
---
name: code-searcher
description: 在代码库里查找某个接口的所有调用方，只读不写
tools: Read, Glob, Grep
model: sonnet
---

你负责在代码库中查找调用关系。只返回文件路径、行号和一句话说明，
不要贴大段代码，结论不超过 20 行。找不到就直接说找不到。
```

## 代价：多 Agent 不是免费的

<figure>
<svg viewBox="0 0 440 460" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="演示结果对比">
  <rect width="440" height="460" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif">
    <text x="220" y="30" fill="#a7f3d0" font-size="17" font-weight="800" text-anchor="middle">演示结果：同样的调研，两种做法</text>
    <g font-size="13">
      <text x="20" y="64" fill="#f4ede4" font-weight="700">单个窗口的峰值（token）</text>
      <text x="100" y="89" fill="#9a93a8" text-anchor="end">单 Agent</text>
      <rect x="110" y="74" width="240" height="22" rx="4" fill="#9a93a8"/>
      <text x="356" y="90" fill="#f4ede4">3,707</text>
      <text x="100" y="117" fill="#9a93a8" text-anchor="end">子 Agent</text>
      <rect x="110" y="102" width="108" height="22" rx="4" fill="#a7f3d0"/>
      <text x="224" y="118" fill="#f4ede4">1,669</text>

      <text x="20" y="158" fill="#f4ede4" font-weight="700">全部调用的累计输入（token）</text>
      <text x="100" y="183" fill="#9a93a8" text-anchor="end">单 Agent</text>
      <rect x="110" y="168" width="240" height="22" rx="4" fill="#9a93a8"/>
      <text x="356" y="184" fill="#f4ede4">24,091</text>
      <text x="100" y="211" fill="#9a93a8" text-anchor="end">多 Agent</text>
      <rect x="110" y="196" width="163" height="22" rx="4" fill="#a7f3d0"/>
      <text x="279" y="212" fill="#f4ede4">16,316</text>

      <text x="20" y="252" fill="#f4ede4" font-weight="700">读取的网页数</text>
      <text x="100" y="277" fill="#9a93a8" text-anchor="end">单 Agent</text>
      <rect x="110" y="262" width="170" height="22" rx="4" fill="#9a93a8"/>
      <text x="286" y="278" fill="#f4ede4">10</text>
      <text x="100" y="305" fill="#9a93a8" text-anchor="end">多 Agent</text>
      <rect x="110" y="290" width="204" height="22" rx="4" fill="#fca5a5"/>
      <text x="320" y="306" fill="#f4ede4">12（有重复）</text>

      <text x="20" y="346" fill="#f4ede4" font-weight="700">耗时（秒）</text>
      <text x="100" y="371" fill="#9a93a8" text-anchor="end">单 Agent</text>
      <rect x="110" y="356" width="198" height="22" rx="4" fill="#9a93a8"/>
      <text x="314" y="372" fill="#f4ede4">3.3</text>
      <text x="100" y="399" fill="#9a93a8" text-anchor="end">多 · 串行</text>
      <rect x="110" y="384" width="240" height="22" rx="4" fill="#ffd38a"/>
      <text x="356" y="400" fill="#f4ede4">4.0</text>
      <text x="100" y="427" fill="#9a93a8" text-anchor="end">多 · 并行</text>
      <rect x="110" y="412" width="84" height="22" rx="4" fill="#a7f3d0"/>
      <text x="200" y="428" fill="#f4ede4">1.4</text>
    </g>
    <text x="220" y="452" fill="#9a93a8" font-size="12" text-anchor="middle">虚构资料、粗估 token；耗时每次运行略有不同</text>
  </g>
</svg>
<figcaption>窗口更小、速度更快，但有重复劳动；真实系统里多 Agent 的总 token 通常更高</figcaption>
</figure>

多 Agent 带来的好处是实打实的，代价也是。下面这张表列出主要的几项：

| 代价 | 表现 | 缓解办法 |
|---|---|---|
| token 成倍增长 | Anthropic 的数据：Agent 约为对话的 4 倍，多 Agent 约 15 倍 | 只在高价值任务上用；按复杂度控制子 Agent 数量；子 Agent 用便宜的模型 |
| 协调开销 | 规划、写派单、汇总都要额外调用模型；主 Agent 要等最慢的子 Agent | 规划和汇总用结构化输出；给子 Agent 设超时和预算 |
| 错误传播 | 计划错了，所有子 Agent 一起错；某个子 Agent 的错误结论被汇总放大 | 汇总时检查来源；关键结论交叉验证；加评审环节 |
| 信息不共享 | 子 Agent 互相不知道对方的进展，重复劳动、决策冲突 | 派单写清边界和共享约定；写操作单线程 |
| 调试困难 | 不确定性叠加，同样的输入每次走的路径都不同 | 完整的追踪；评估看结果而不是路径 |
| 状态与恢复 | 运行时间长，中途出错从头再来代价很大 | 检查点、重试、从断点恢复 |

### 同步等待的瓶颈

Anthropic 的系统里，主 Agent 是**同步**等待子 Agent 的：派出一批，等全部完成，再决定下一步。他们自己也指出了问题：主 Agent 没法在中途调整子 Agent 的方向，子 Agent 之间不能协调，一个慢的子 Agent 会拖住整个系统。

改成异步可以解决这些问题，但会带来新的复杂度：结果怎么协调、状态怎么保持一致、错误怎么在子 Agent 之间传播。这和后端里从同步 RPC 换成消息队列时遇到的问题几乎一样（见本系列《消息队列》）。

### 错误会叠加

单 Agent 出错，最多是一条链路错了。多 Agent 系统里，错误有更多的传播路径。2025 年的一篇论文（Cemri et al.，Why Do Multi-Agent LLM Systems Fail?）分析了多个开源多 Agent 框架的运行轨迹，把失败归纳为 14 种模式、3 大类：

- **系统设计问题**：比如角色定义不清、不遵守任务要求、不知道何时结束；
- **Agent 之间没对齐**：比如信息没传递、无视其他 Agent 的输入、推理和行动不一致；
- **任务验证问题**：比如过早结束、验证不充分或者干脆没有验证。

这份分类和前面讲的派单、汇总、评审几乎一一对应：多 Agent 系统的很多失败，不是模型能力不够，而是**沟通和组织**出了问题。Cognition 在 2026 年的文章里也说了类似的话：剩下的开放问题，全都是沟通问题。

### 状态与上线

多 Agent 系统一次运行可能持续很久、调用很多工具。Anthropic 提到了几条生产经验：

- 出错时从头再来代价太大，所以系统要支持**从断点恢复**，加上重试，并在工具失败时让 Agent 自己调整；
- 发布新版本时，正在运行的 Agent 可能处于任何一步，不能简单地一次性替换。他们采用**彩虹部署**（rainbow deployment）：新旧版本同时运行，流量逐步迁移到新版本。

## 什么任务适合，什么任务不适合

<figure>
<svg viewBox="0 0 440 470" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="要不要用多 Agent 的决策流程">
  <rect width="440" height="470" fill="#0f0e1c"/>
  <defs><marker id="ma-a5" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9a93a8"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif">
    <text x="220" y="30" fill="#a7f3d0" font-size="17" font-weight="800" text-anchor="middle">要不要上多 Agent？</text>
    <g font-size="14" fill="#f4ede4" text-anchor="middle">
      <rect x="20" y="48" width="250" height="56" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="145" y="71">单 Agent + 好工具 + 上下文管理</text>
      <text x="145" y="93">已经够用？</text>
      <rect x="20" y="138" width="250" height="56" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="145" y="161">能拆成互不依赖、</text>
      <text x="145" y="183">可以并行的子任务？</text>
      <rect x="20" y="228" width="250" height="56" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="145" y="251">子任务要共享大量上下文，</text>
      <text x="145" y="273">或同时修改同一份产物？</text>
      <rect x="20" y="318" width="250" height="56" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
      <text x="145" y="341">任务价值撑得起</text>
      <text x="145" y="363">几倍的 token 消耗？</text>
      <rect x="20" y="408" width="250" height="42" rx="10" fill="rgba(167,243,208,.18)" stroke="#a7f3d0"/>
      <text x="145" y="434" fill="#a7f3d0" font-weight="800">主管-工人 / 并行扇出</text>
    </g>
    <g stroke="#9a93a8" stroke-width="2">
      <line x1="145" y1="104" x2="145" y2="136" marker-end="url(#ma-a5)"/>
      <line x1="145" y1="194" x2="145" y2="226" marker-end="url(#ma-a5)"/>
      <line x1="145" y1="284" x2="145" y2="316" marker-end="url(#ma-a5)"/>
      <line x1="145" y1="374" x2="145" y2="406" marker-end="url(#ma-a5)"/>
      <line x1="270" y1="76" x2="310" y2="76" marker-end="url(#ma-a5)"/>
      <line x1="270" y1="166" x2="310" y2="166" marker-end="url(#ma-a5)"/>
      <line x1="270" y1="256" x2="310" y2="256" marker-end="url(#ma-a5)"/>
      <line x1="270" y1="346" x2="310" y2="346" marker-end="url(#ma-a5)"/>
    </g>
    <g font-size="13" fill="#9a93a8">
      <text x="155" y="125">不够</text>
      <text x="155" y="215">能</text>
      <text x="155" y="305">否</text>
      <text x="155" y="395">是</text>
      <text x="290" y="68" text-anchor="middle">够</text>
      <text x="290" y="158" text-anchor="middle">不能</text>
      <text x="290" y="248" text-anchor="middle">是</text>
      <text x="290" y="338" text-anchor="middle">否</text>
    </g>
    <g font-size="13" fill="#f4ede4" text-anchor="middle">
      <rect x="312" y="60" width="118" height="32" rx="8" fill="rgba(255,255,255,.04)" stroke="#9a93a8"/>
      <text x="371" y="81">别拆</text>
      <rect x="312" y="150" width="118" height="32" rx="8" fill="rgba(255,255,255,.04)" stroke="#9a93a8"/>
      <text x="371" y="171">单 Agent / 流水线</text>
      <rect x="312" y="240" width="118" height="32" rx="8" fill="rgba(255,255,255,.04)" stroke="#9a93a8"/>
      <text x="371" y="261">单写者 + 评审</text>
      <rect x="312" y="330" width="118" height="32" rx="8" fill="rgba(255,255,255,.04)" stroke="#9a93a8"/>
      <text x="371" y="351">先缩小规模</text>
    </g>
  </g>
</svg>
<figcaption>四个问题依次过一遍，大多数任务在前两步就有答案</figcaption>
</figure>

把前面的内容合起来，判断一个任务适不适合多 Agent，主要看三点：**能不能拆成独立的部分**、**各部分需要共享多少上下文**、**值不值得花这么多 token**。

### 适合的任务

| 任务特征 | 例子 | 为什么适合 |
|---|---|---|
| 广度优先的调研 | 行业调研、竞品分析、技术选型、文献综述 | 方向多且互相独立；每个方向读得多、结论少 |
| 可以独立并行的子任务 | 批量审查一批文档、对多个数据源分别做分析 | 天然可拆；并行直接缩短时间 |
| 信息量超过单个窗口 | 在大型代码库里查找、分析大量日志 | 隔离让每个窗口只装一部分 |
| 需要独立视角的检查 | 代码评审、事实核查、合规检查 | 评审者没有被生成过程影响 |
| 需要很多复杂工具 | 一个 Agent 要对接几十个工具 | 按领域拆分，每个 Agent 只管几个工具 |

Anthropic 根据他们的产品数据（用 Clio 做的隐私保护分析）列出了调研功能最常见的用途：开发软件系统（10%）、撰写专业和技术内容（8%）、制定业务增长策略（8%）、辅助学术研究与教学材料（7%）、核实人物、地点或组织的信息（5%）。

### 不适合的任务

| 任务特征 | 例子 | 为什么不适合 |
|---|---|---|
| 子任务之间强依赖 | 后一步的设计依赖前一步的细节 | 并行不起来，拆开只增加沟通成本 |
| 需要共享大量上下文 | 多数编码任务：改一个功能要牵动多个文件 | 每个子 Agent 都要知道全局约定，否则决策冲突 |
| 需要实时协调 | 多个 Agent 边做边互相调整 | 目前的模型还不擅长实时的协调与委派 |
| 简单、低价值的任务 | 回答一个事实问题、改一个错别字 | 几倍的 token 换不来相应的价值 |

**编码任务要特别谨慎。** Anthropic 在文章里明确说，多数编码任务能真正并行的子任务比调研少。Cognition 的两篇文章也都以编码为背景。但这不等于编码完全不能用多 Agent，而是要选对方式：

- **只读的探索型子 Agent**：查调用关系、读文档、跑测试看日志，只返回结论，不改代码；
- **独立的评审 Agent**：不共享写代码时的上下文，只看 diff；
- **真正互不相关的任务并行**：比如两个不相关模块的 bug，各自在独立的工作区（如 git worktree）里修改，最后由人或者主 Agent 合并；
- **同一个功能的修改，交给一个写者**。

### 业界的正反经验

把几家的公开经验放在一起看：

| 来源 | 观点 | 背景 |
|---|---|---|
| Anthropic（2025 年 6 月） | 主管-工人结构在开放式调研上大幅优于单 Agent；代价是约 15 倍于对话的 token | 广度优先的网络调研 |
| Cognition（2025 年 6 月） | 不要构建多 Agent：要共享完整上下文，冲突的决定带来糟糕的结果；首选单线程的线性 Agent | 编程 Agent |
| Cognition（2026 年 4 月） | 写操作单线程、其他 Agent 贡献智力而非动作时，多 Agent 有效；独立上下文的评审 Agent、主管拆分任务给子 Agent 已在生产中使用 | 编程 Agent |
| OpenAI Agents SDK 文档 | 提供 agents as tools 与 handoff 两种机制；代码编排更可预测，LLM 编排更灵活，二者可以混用 | 通用框架 |
| Anthropic（2024 年 12 月） | 先用最简单的方案；只有测量证明有提升时才增加复杂度 | 通用建议 |

Cognition 前后两篇文章的变化很能说明问题：从「不要构建多 Agent」到「这些多 Agent 用法确实有效」，不是立场反转，而是找到了不违反原则的用法：**多个 Agent 一起想，一个 Agent 动手**。

## 评估与可观测

### 评估：看结果，不看路径

多 Agent 系统每次运行走的路径都可能不同：开了几个子 Agent、搜了什么、读了哪些页。即使两次都得到正确答案，过程也可能完全不一样。所以评估要**看结果是否正确、过程是否合理**，而不是检查它是否按预设的步骤走。

Anthropic 分享的几条做法：

- **尽早开始，小样本即可**。开发早期，提示词的一点改动就可能让效果大幅变化，大约 20 个有代表性的问题就足以看出差别，不必等到有几百条测试用例；
- **用 LLM 当评委**。用一次模型调用，按一份评分标准给输出打 0.0～1.0 的分并判定是否通过，标准包括事实准确性、引用准确性、完整性、来源质量、工具使用效率。他们发现单个评委调用比多个评委更稳定、与人工判断更一致；
- **人工评估不能省**。人工测试发现了自动评估漏掉的问题，比如早期的 Agent 偏爱 SEO 优化过的内容农场，而不是权威但排名靠后的来源。

还有一条容易被忽略：**一定要和单 Agent 基线比**，而且最好在相近的 token 预算下比。如果多 Agent 的提升主要来自「花了更多 token」，那给单 Agent 同样的预算（比如更长的思考、更多的工具调用）也许能得到类似的效果，而系统要简单得多。评估方法详见本系列《评估（Evals）》。

### 可观测：追踪每一个子 Agent

多 Agent 系统出问题时，最常听到的抱怨是「不知道哪一步错了」。解决办法和微服务一样：**分布式追踪**（见本系列《可观测性》）。把一次任务看成一个 trace，每个 Agent 是一个 span，每次模型调用和工具调用是更下一级的 span：

```text
trace: 选型调研 #8f2a
├─ lead/plan         输入 20 tok    输出 235 tok   → 3 份派单
├─ sub1 性能          6 次调用  峰值 1,669 tok   5 次工具   1.1s
│   ├─ llm  → web_search("向量库 性能 对比")
│   ├─ tool web_search   0.2s
│   ├─ llm  → fetch("/overview")
│   └─ ...
├─ sub2 成本          6 次调用  峰值 1,664 tok   5 次工具   1.1s
├─ sub3 生态          6 次调用  峰值 1,638 tok   5 次工具   1.1s
└─ lead/synth        输入 286 tok   输出 163 tok
```

每个 span 上值得记录的属性：

| 层级 | 记录什么 | 用来发现什么 |
|---|---|---|
| 任务 | 子 Agent 数量、总 token、总耗时、最终评分 | 成本是否失控、规模是否和任务复杂度匹配 |
| 子 Agent | 收到的派单原文、返回的结论原文、调用次数、峰值上下文、是否触发停止条件 | 派单是否含糊、子 Agent 是否停不下来 |
| 模型调用 | 输入输出 token、延迟、选择了哪个工具 | 哪一步最贵、是否选错工具 |
| 工具调用 | 参数、耗时、结果大小、是否失败 | 慢工具、失败重试、结果过大 |

在这些数据上再算几个**跨 Agent 的指标**，会很有用：

- **重复率**：多个子 Agent 读了同一个来源、做了同样的搜索的比例。重复率高，说明派单的边界没划清；
- **等待时间**：主 Agent 等最慢那个子 Agent 的时间。长尾明显，说明需要超时或者拆得更均匀；
- **结论采纳率**：子 Agent 的结论有多少出现在最终结果里。很低的话，说明派了很多无用的活；
- **冲突数**：汇总时发现的事实冲突和决策冲突数量。

Anthropic 提到，他们加了完整的生产追踪之后，才能系统地诊断 Agent 为什么失败；同时出于隐私考虑，他们监控的是 Agent 的**决策模式和交互结构**，而不是具体的对话内容。

## 常见的坑

### 1. 为了「看起来高级」而拆

任务本身一个 Agent 就能做好，却拆成规划者、执行者、审核者、总结者四个 Agent 来回传话。每多一次传递，就多一次信息损失和一次模型调用。先做单 Agent 基线，确认它在哪里不行，再决定拆什么。

### 2. 派单只有一句话

「研究一下 X」这样的派单，几乎一定会导致重复劳动或答非所问。派单要写清目标、边界、输出格式、停止条件，像给一个刚入职、对项目一无所知的同事写任务说明。

### 3. 子 Agent 返回原文

子 Agent 把读到的整页内容都交回来，主 Agent 的窗口又被塞满了，隔离的好处全部丢失。要在派单里规定输出格式和长度上限；大块产出写到文件或存储里，只交回引用。

### 4. 多个 Agent 同时写同一份产物

两个子 Agent 各自改同一个文件、各自写报告的不同章节却不知道对方的口径，最后拼起来风格不一、互相矛盾。写操作保持单线程，其他 Agent 只提供信息。

### 5. 没有停止条件和预算

子 Agent 不知道什么时候算「够了」，就会一直搜下去；主 Agent 不知道该开几个子 Agent，就可能为一个简单问题开几十个。要给每个子 Agent 设工具调用上限和超时，给整个任务设 token 预算。

### 6. 评审循环不收敛

评审标准模糊（「写得更好一点」），生成者每轮都在改，评审者每轮都不满意。评审标准要尽量具体、可检查；设轮数上限，超过就交给人。

### 7. 交接来回踢皮球

交接模式里，A 觉得该 B 处理，B 觉得该 A 处理，用户被转来转去。每个 Agent 的职责描述要互斥、覆盖完整，并限制一次对话内的交接次数。

### 8. 只看最终结果，不看过程数据

最终答案错了，却不知道是计划错了、派单错了、某个子 Agent 搜错了，还是汇总时丢了信息。从第一天起就记录每个子 Agent 的派单、返回和 token，否则调试只能靠猜。

## 高频面试题速答

**Q：什么时候应该用多 Agent，而不是单 Agent？**
当任务能拆成互不依赖、可以并行的子任务，每个子任务需要读大量信息但只产出少量结论，并且任务价值撑得起几倍的 token 成本时。典型是广度优先的调研。先做单 Agent 基线，确认瓶颈之后再拆。

**Q：子 Agent 的核心价值是什么？**
上下文隔离和并行。每个子 Agent 在自己的窗口里探索，只返回精简结论，主 Agent 的窗口保持干净；多个子 Agent 同时运行，总耗时接近最慢的那一个。此外还能针对子任务定制提示词、工具和模型。

**Q：主管-工人和交接（handoff）有什么区别？**
控制权在谁手里。主管-工人模式里，主管把子 Agent 当工具调用，结果交回主管，主管始终掌控对话；交接模式里，当前 Agent 把整个对话交给另一个 Agent，由接手者直接继续和用户对话。

**Q：给子 Agent 派任务要写哪些内容？**
目标、边界（不做什么、和别人怎么分工）、输出格式（结构和长度上限）、停止条件（读够多少、调用上限）；可选的还有建议的工具与来源、已知事实和共享约定。子 Agent 看不到主 Agent 的上下文，派单就是它的全部信息。

**Q：多 Agent 的主要代价有哪些？**
token 成倍增长（Anthropic 的数据是约 15 倍于普通对话）；规划、派单、汇总带来的协调开销；错误在 Agent 之间传播和放大；子 Agent 之间信息不共享导致重复和冲突；不确定性叠加导致调试困难。

**Q：为什么说多数编码任务要谨慎使用多 Agent？**
编码任务的子任务之间往往强依赖，需要共享大量上下文（命名、接口、风格）。多个 Agent 并行修改，各自做出的隐含决定会冲突。比较稳妥的做法是写操作单线程，其他 Agent 只做只读探索或独立评审。

**Q：子 Agent 返回的结果相互矛盾怎么办？**
区分两类冲突。事实冲突：保留双方说法和来源，按来源可信度判断，必要时派一个子 Agent 专门核实。决策冲突（风格、接口不一致）：很难事后合并，应该在派单里事先约定，或者让唯一的写者来做决定。

**Q：怎么评估和调试多 Agent 系统？**
评估看结果而不是路径，可以用 LLM 评委按评分标准打分，配合人工抽查，并和相同预算的单 Agent 基线比较。调试靠分布式追踪：每个子 Agent 一个 span，记录派单、返回、token、耗时和工具调用，再看重复率、等待时间、结论采纳率等跨 Agent 指标。

## 总结

- 单 Agent 有三个瓶颈：**上下文装不下、只能串行、角色混杂**。很多时候在单 Agent 内部就能缓解，先做单 Agent 基线；
- 五种常见拓扑：**主管-工人**（动态拆分）、**并行扇出**（固定并行）、**流水线**（固定顺序）、**生成者 + 评审者**（独立挑错）、**交接**（转交控制权）；
- 子 Agent 的价值是**上下文隔离与并行**：各自探索、只回结论，总耗时接近最慢的那一个；本质上是帮系统**花够 token**；
- **派单**写清目标、边界、输出格式、停止条件；按任务复杂度决定投入；
- **汇总**要统一格式、去重；事实冲突保留来源，决策冲突事前避免；**写操作保持单线程**；
- 代价是 **token 成倍增长、协调开销、错误传播、调试困难**；
- 适合**广度优先的调研、可独立并行的子任务**；不适合**强依赖、需要共享大量上下文**的任务，多数编码任务要谨慎；
- 评估看结果、和单 Agent 基线比；用**分布式追踪**记录每个子 Agent 的派单、返回和成本。

<div class="refs" markdown="1">

### 参考资料

- Anthropic Engineering (2025). How we built our multi-agent research system.
- Anthropic Engineering (2024). Building effective agents.
- Anthropic Engineering (2025). Effective context engineering for AI agents.
- Cognition Blog (2025). Don't Build Multi-Agents.
- Cognition Blog (2026). Multi-Agents: What's Actually Working.
- OpenAI Agents SDK 文档：Handoffs；Agent orchestration（Orchestrating multiple agents）.
- Claude Code 文档：Subagents.
- Du, Y., et al. (2023). Improving Factuality and Reasoning in Language Models through Multiagent Debate. arXiv:2305.14325.
- Cemri, M., et al. (2025). Why Do Multi-Agent LLM Systems Fail? arXiv:2503.13657.
- Python 文档：concurrent.futures — Launching parallel tasks；asyncio — Coroutines and Tasks.

</div>
