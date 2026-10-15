title: Agent 的记忆：让 AI 记住你，也懂得忘记
subtitle: 模型为什么每次调用都「失忆」，短期与长期记忆的分层，语义、情景、程序三类记忆，写入、存储、检索、更新、遗忘的完整生命周期，与 RAG 的异同，主流产品的做法，隐私与记忆投毒，附一个标准库实现的小型记忆系统
tag: AI 与大模型
color: #fcd5ce

## 它为什么总是不记得你

你跟 AI 助手说过：「我是后端工程师，平时用 Go，回答简短一点，先给结论。」那次聊得很顺。第二天新开一个对话，问它限流怎么做，它又从「限流是一种保护系统的手段」讲起，示例代码用的是 Python。

这不是「记性不好」，而是**模型本身根本没有记性**。同一个对话里它「记得」前面的话，是因为客户端每次都把整段聊天记录重新发了一遍；开了新对话，这些记录不在请求里，模型就什么都不知道。

所以 Agent 的「记忆」是模型**外面**的一套工程：哪些信息值得留下、存在哪里、什么时候取出来放回上下文、过时了怎么改、什么时候删掉。本文把这套工程拆开来讲。

> 本文默认你了解大模型调用和上下文窗口的基本概念，见本系列《什么是 LLM》。检索部分会用到《Embedding 向量》和《RAG 是什么》中的知识。

## 模型是无状态的：每次调用都「失忆」

### 对话是怎么「记住」上文的

调用大模型时，你发送的是一个**消息列表**：系统提示、用户消息、模型回复……模型据此生成下一条回复。服务端处理完请求后不会为你保留任何东西（缓存只是性能优化，不改变语义，见同批文章《Token 与 KV Cache》）。所以「对话」是客户端拼出来的：聊天应用把历史存在数据库里，每轮整段发给模型；新对话就是一个空白的模型；模型权重也不会因为和你聊天而改变。

### 为什么不把所有历史都塞进去

既然「记忆」就是往上下文里放东西，最省事的做法是把用户所有的历史对话都塞进去。这条路走不远：

| 问题 | 说明 |
|---|---|
| 放不下 | 上下文窗口再大也有上限，一个活跃用户几个月的对话轻松超过 |
| 贵、慢 | 输入越长，费用和首字延迟越高，每一轮都要为这些历史付费 |
| 效果变差 | 无关信息越多，模型越容易被干扰，关键信息反而被「淹没」 |
| 信息冲突 | 用户三个月前说用 Go，上周说改用 Rust，两句话都在上下文里，模型该信哪个 |

所以记忆系统的核心是一个**选择问题**：下一次调用时，从所有可能有用的信息里挑出最值得放进上下文的那一小部分。这和同批文章《上下文工程》讨论的是同一件事。

<figure>
<svg viewBox="0 0 440 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="无状态模型与外挂记忆">
  <rect width="440" height="360" fill="#0f0e1c"/>
  <defs><marker id="am-a1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#fcd5ce"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="30" fill="#fcd5ce" font-size="18" font-weight="800">记忆在模型外面</text>
    <rect x="14" y="62" width="96" height="60" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="62" y="89" fill="#f4ede4" font-size="15" font-weight="700">用户</text>
    <text x="62" y="110" fill="#9a93a8" font-size="13">新消息</text>
    <line x1="110" y1="92" x2="146" y2="92" stroke="#fcd5ce" stroke-width="2.5" marker-end="url(#am-a1)"/>
    <rect x="150" y="52" width="140" height="80" rx="12" fill="rgba(252,213,206,.14)" stroke="#fcd5ce"/>
    <text x="220" y="86" fill="#fcd5ce" font-size="16" font-weight="800">Agent 程序</text>
    <text x="220" y="110" fill="#9a93a8" font-size="13">拼装上下文</text>
    <line x1="290" y1="80" x2="326" y2="80" stroke="#fcd5ce" stroke-width="2.5" marker-end="url(#am-a1)"/>
    <line x1="330" y1="104" x2="294" y2="104" stroke="#9a93a8" stroke-width="2.5" marker-end="url(#am-a1)"/>
    <rect x="330" y="62" width="96" height="60" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="378" y="89" fill="#f4ede4" font-size="15" font-weight="700">LLM</text>
    <text x="378" y="110" fill="#9a93a8" font-size="13">无状态</text>
    <line x1="200" y1="132" x2="200" y2="216" stroke="#9a93a8" stroke-width="2.5" marker-end="url(#am-a1)"/>
    <line x1="240" y1="220" x2="240" y2="136" stroke="#fcd5ce" stroke-width="2.5" marker-end="url(#am-a1)"/>
    <text x="190" y="180" fill="#9a93a8" font-size="13" text-anchor="end">回答后写入</text>
    <text x="250" y="180" fill="#fcd5ce" font-size="13" text-anchor="start">调用前读取</text>
    <rect x="150" y="220" width="140" height="64" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="220" y="248" fill="#f4ede4" font-size="15" font-weight="700">记忆库</text>
    <text x="220" y="270" fill="#9a93a8" font-size="13">文件 · 数据库 · 向量</text>
    <text x="220" y="318" fill="#f4ede4" font-size="14">模型每次只看本次请求里的内容</text>
    <text x="220" y="342" fill="#9a93a8" font-size="13">要它「记得」，就得每次把相关记忆放回上下文</text>
  </g>
</svg>
<figcaption>模型不保存任何状态。记忆系统在调用前从记忆库取出相关内容拼进上下文，回答后再把新信息写回去</figcaption>
</figure>

### 记忆不是什么

- **不是微调**：把用户信息训练进权重慢、贵，也没法「删掉某一条」（见《微调与 LoRA》）；
- **不是聊天记录本身**：聊天记录是原始素材，记忆是挑选、整理过的信息；
- **不是知识库检索**：RAG 回答「世界上的知识」，记忆回答「关于这个用户、这个任务，我之前知道什么」，后面专门对比。

## 记忆的分层：短期与长期

<figure>
<svg viewBox="0 0 440 420" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="记忆分层">
  <rect width="440" height="420" fill="#0f0e1c"/>
  <defs><marker id="am-a2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#fcd5ce"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <rect x="14" y="14" width="412" height="206" rx="14" fill="rgba(252,213,206,.06)" stroke="#fcd5ce"/>
    <text x="220" y="42" fill="#fcd5ce" font-size="16" font-weight="800">上下文窗口：短期 / 工作记忆</text>
    <rect x="30" y="58" width="380" height="30" rx="8" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="220" y="78" fill="#f4ede4" font-size="14">系统提示</text>
    <rect x="30" y="96" width="380" height="30" rx="8" fill="rgba(252,213,206,.16)" stroke="#fcd5ce"/>
    <text x="220" y="116" fill="#fcd5ce" font-size="14" font-weight="700">常驻记忆：用户档案、偏好与规则</text>
    <rect x="30" y="134" width="380" height="30" rx="8" fill="rgba(252,213,206,.16)" stroke="#fcd5ce"/>
    <text x="220" y="154" fill="#fcd5ce" font-size="14" font-weight="700">检索到的记忆：与本轮问题相关</text>
    <rect x="30" y="172" width="380" height="30" rx="8" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="220" y="192" fill="#f4ede4" font-size="14">本次会话的消息与工具结果</text>
    <rect x="14" y="252" width="412" height="154" rx="14" fill="rgba(255,255,255,.03)" stroke="#9a93a8" stroke-dasharray="6 5"/>
    <line x1="80" y1="262" x2="80" y2="224" stroke="#fcd5ce" stroke-width="2.5" marker-end="url(#am-a2)"/>
    <line x1="220" y1="262" x2="220" y2="224" stroke="#fcd5ce" stroke-width="2.5" marker-end="url(#am-a2)"/>
    <line x1="360" y1="262" x2="360" y2="224" stroke="#fcd5ce" stroke-width="2.5" marker-end="url(#am-a2)"/>
    <text x="94" y="246" fill="#9a93a8" font-size="13" text-anchor="start">常驻</text>
    <text x="234" y="246" fill="#9a93a8" font-size="13" text-anchor="start">检索</text>
    <text x="374" y="246" fill="#9a93a8" font-size="13" text-anchor="start">常驻</text>
    <rect x="22" y="264" width="124" height="80" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="84" y="296" fill="#f4ede4" font-size="15" font-weight="700">语义记忆</text>
    <text x="84" y="320" fill="#9a93a8" font-size="13">事实与偏好</text>
    <rect x="158" y="264" width="124" height="80" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="220" y="296" fill="#f4ede4" font-size="15" font-weight="700">情景记忆</text>
    <text x="220" y="320" fill="#9a93a8" font-size="13">发生过的事</text>
    <rect x="294" y="264" width="124" height="80" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="356" y="296" fill="#f4ede4" font-size="15" font-weight="700">程序记忆</text>
    <text x="356" y="320" fill="#9a93a8" font-size="13">做事的方法</text>
    <text x="220" y="384" fill="#9a93a8" font-size="14">窗口外：长期记忆（跨会话，存在外部）</text>
  </g>
</svg>
<figcaption>短期记忆就是上下文窗口里的内容；长期记忆存在窗口外，要么每次常驻加载，要么按问题检索进来</figcaption>
</figure>

### 短期记忆：上下文窗口里的一切

**短期记忆**（也叫工作记忆）就是本次调用的上下文：系统提示、会话消息、工具结果、模型的中间笔记。模型能直接看到它，但容量受窗口限制，会话结束就消失。

上下文快满时，可以丢掉最早的消息、把旧消息压缩成摘要、把大段工具结果换成简短引用。MemGPT 论文的做法是：被挤出消息队列的内容生成一份**递归摘要**（新摘要 = 旧摘要 + 被挤出的消息）放在队列开头，原文另存到外部，需要时还能搜回来。

### 长期记忆：跨会话保留的信息

**长期记忆**存在上下文之外（文件、数据库、向量库），容量几乎不受限，但必须在合适的时候被**读进**上下文才有用。读进来的方式有两种，这是设计时最重要的区分：

| | 常驻加载 | 按需检索 |
|---|---|---|
| 做法 | 每次会话开始都放进系统提示 | 根据当前问题搜索，取最相关的几条 |
| 适合 | 条数少、几乎每轮都用得上：用户名字、角色、回答风格、项目约定 | 条数多、只在特定话题下有用：过去讨论过的某个方案、某次故障 |
| 优点 | 一定能看到，不会漏 | 能容纳大量记忆，不占用固定的上下文 |
| 缺点 | 占用固定的上下文，条数一多就挤 | 可能检索不到；检索质量决定效果 |
| 例子 | CLAUDE.md、ChatGPT 的记忆摘要、MemGPT 的 working context | 搜索过去的对话、向量库中的事件记录 |

常见误区是「所有记忆都走向量检索」。「回答先给结论」和「帮我设计一个限流方案」语义上毫无关系，检索不到，可它恰恰是每次都该遵守的规则。

## 长期记忆的三种类型

Agent 领域借用了认知科学的术语。2023 年的论文 *Cognitive Architectures for Language Agents*（CoALA）把语言 Agent 的记忆分为工作记忆（当前决策周期的信息）、情景记忆（过去的经历）、语义记忆（关于世界和自身的知识）和程序记忆（隐式的模型权重，加上显式的代码与提示）。落到工程上，长期记忆大致是三种：

| 类型 | 记什么 | 例子 | 常见形式 |
|---|---|---|---|
| **语义记忆** | 稳定的事实和偏好 | 用户是后端工程师；主力语言是 Go；项目用 PostgreSQL | 键值对、档案字段、一句话事实 |
| **情景记忆** | 发生过的具体事件，带时间 | 10 月 3 日讨论了限流方案，选了令牌桶；上周登录接口被刷过一次 | 带时间戳的事件记录、会话摘要 |
| **程序记忆** | 做事的方法、规则、技能 | 回答先给结论；这个仓库提交前要跑 `make lint`；部署要先灰度 | 系统提示里的规则、指令文件、可复用的技能包 |

- **情景记忆可以提炼成语义记忆**：用户三次要求「给 Go 示例」，可以归纳成「用户偏好 Go」。Generative Agents 论文的「反思」就是这样：近期事件的重要性累计超过阈值（论文实现里是 150）时，让模型归纳出更高层的观点存回去；
- **程序记忆最接近「指令」**：它直接改变 Agent 的行为，写入要格外谨慎。CLAUDE.md、同批文章《Skills 技能包》讲的技能包都可以看作显式的程序记忆；
- **类比不要过度**：人的记忆会重构、受情绪影响，和数据库记录不是一回事。分类的价值只在于提醒你：不同类型的信息，写入时机、存储、检索和过期策略都不一样。

## 记忆的生命周期

<figure>
<svg viewBox="0 0 440 310" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="记忆的生命周期">
  <rect width="440" height="310" fill="#0f0e1c"/>
  <defs><marker id="am-a3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#fcd5ce"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="30" fill="#fcd5ce" font-size="18" font-weight="800">记忆的五个环节</text>
    <rect x="164" y="50" width="112" height="56" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="220" y="75" fill="#f4ede4" font-size="16" font-weight="700">更新</text>
    <text x="220" y="96" fill="#9a93a8" font-size="13">新值覆盖旧值</text>
    <line x1="220" y1="106" x2="220" y2="131" stroke="#fcd5ce" stroke-width="2.5" marker-end="url(#am-a3)"/>
    <rect x="10" y="135" width="124" height="60" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="72" y="161" fill="#f4ede4" font-size="16" font-weight="700">写入</text>
    <text x="72" y="182" fill="#9a93a8" font-size="13">何时·写啥·谁写</text>
    <line x1="134" y1="165" x2="160" y2="165" stroke="#fcd5ce" stroke-width="2.5" marker-end="url(#am-a3)"/>
    <rect x="164" y="135" width="112" height="60" rx="12" fill="rgba(252,213,206,.16)" stroke="#fcd5ce"/>
    <text x="220" y="161" fill="#fcd5ce" font-size="16" font-weight="800">存储</text>
    <text x="220" y="182" fill="#9a93a8" font-size="13">文件·向量·图</text>
    <line x1="276" y1="165" x2="302" y2="165" stroke="#fcd5ce" stroke-width="2.5" marker-end="url(#am-a3)"/>
    <rect x="306" y="135" width="124" height="60" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="368" y="161" fill="#f4ede4" font-size="16" font-weight="700">检索</text>
    <text x="368" y="182" fill="#9a93a8" font-size="13">相关·新鲜·重要</text>
    <line x1="220" y1="195" x2="220" y2="221" stroke="#fcd5ce" stroke-width="2.5" marker-end="url(#am-a3)"/>
    <rect x="164" y="225" width="112" height="56" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="220" y="250" fill="#f4ede4" font-size="16" font-weight="700">遗忘</text>
    <text x="220" y="271" fill="#9a93a8" font-size="13">过期·衰减·删除</text>
  </g>
</svg>
<figcaption>存储在中间：写入把信息放进来，检索把信息取出去，更新修正旧信息，遗忘把不再需要的信息清理掉</figcaption>
</figure>

### 写入：何时写、写什么、谁来写

**何时写**有三种常见时机：

| 时机 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| 每轮对话后（热路径） | 回复后立即抽取并写入 | 下一轮就能用上 | 增加每轮的延迟和成本 |
| 会话结束后 | 对整段会话做一次总结和抽取 | 信息更完整，能看到前后文 | 会话中途崩溃可能丢失 |
| 后台定时（冷路径） | 定期批量处理一段时间的对话 | 不影响响应速度，可以做归纳整理 | 有延迟，新信息要等一段时间才生效 |

Claude 网页版官方帮助中心的说明是：基于聊天记录的记忆摘要**每 24 小时**更新一次，这就是典型的冷路径。

**写什么**更难。实用标准：**将来有用**、**相对稳定**、**无法从别处轻易得到**。Claude Code 的 auto memory 文档有类似原则：能从代码库推导出来的（架构、文件路径）不记，CLAUDE.md 里已有的不记。寒暄、一次性请求、模型自己的推测、敏感信息都不该写。

写成什么样子也有讲究：**自包含**（「他下周出差」三个月后毫无意义，应写成「用户 2026-10-20 至 10-24 在上海出差」）；**原子化**（一条只说一件事，方便单独更新和删除）；**保留来源**（用户亲口说的，还是从工具结果里读到的）。

**谁来写**是两种不同的架构：

| | 模型主动写 | 后台抽取 |
|---|---|---|
| 做法 | 给模型一个「写记忆」工具，它自己决定何时调用 | 另一条流程（通常是另一次 LLM 调用）分析对话，抽取出要记的内容 |
| 代表 | MemGPT 用函数调用编辑记忆；Claude API 的 memory tool | Mem0 的抽取—更新流水线；聊天产品的周期性记忆摘要 |
| 优点 | 写入时机和内容由理解上下文的模型决定，用户可以直接说「记住这个」 | 不打扰主任务，抽取的规则和提示词可以单独调优 |
| 缺点 | 占用主任务的注意力，模型可能忘了写或写太多 | 多一次调用的成本；可能抽取出用户没打算留下的信息 |

两者常常并存：用户明确说「记住」时立即写，其余交给后台整理。

### 存储：文件、键值、向量库、知识图谱

| 存储形式 | 适合存什么 | 优点 | 缺点 | 例子 |
|---|---|---|---|---|
| **文件 / Markdown** | 规则、项目约定、少量档案 | 人能直接读和改，可以纳入版本控制，模型读写方便 | 量大了难以检索，只能整份加载或按文件名查找 | CLAUDE.md；Claude API memory tool 的 `/memories` 目录 |
| **键值 / 关系数据库** | 结构化的档案字段：语言、时区、套餐 | 精确读写，天然支持「同一个 key 新值覆盖旧值」 | 只能存事先设计好的字段，不擅长自由文本 | 用户档案表 |
| **向量库** | 大量自由文本：事件、会话摘要、过去的对话片段 | 按语义检索，能处理措辞不同但意思相近的问题 | 检索有不确定性；更新和删除需要同步维护索引 | 搜索过去的对话；Generative Agents 的记忆流 |
| **知识图谱** | 实体之间的关系：谁负责哪个服务，哪个服务依赖哪个库 | 能做多跳推理，关系变化时更新精确 | 抽取实体和关系成本高、容易出错，系统更复杂 | Mem0 的图记忆变体 |

真实系统通常混合使用：档案用键值存并常驻，事件和摘要进向量库检索，关系复杂的领域再加图。很多场景一个 Markdown 文件就够了，不必一开始就上最复杂的方案。

### 检索：相关性、新鲜度、重要性

<figure>
<svg viewBox="0 0 440 330" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="检索打分">
  <rect width="440" height="330" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="30" fill="#fcd5ce" font-size="17" font-weight="800">总分 = 相关性 + 新鲜度 + 重要性</text>
    <rect x="10" y="48" width="132" height="90" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="76" y="76" fill="#f4ede4" font-size="16" font-weight="700">相关性</text>
    <text x="76" y="100" fill="#9a93a8" font-size="13">问题与记忆的</text>
    <text x="76" y="120" fill="#9a93a8" font-size="13">向量相似度</text>
    <rect x="154" y="48" width="132" height="90" rx="12" fill="rgba(252,213,206,.16)" stroke="#fcd5ce"/>
    <text x="220" y="76" fill="#fcd5ce" font-size="16" font-weight="800">新鲜度</text>
    <text x="220" y="100" fill="#9a93a8" font-size="13">距上次被用到</text>
    <text x="220" y="120" fill="#9a93a8" font-size="13">越久越低</text>
    <rect x="298" y="48" width="132" height="90" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="364" y="76" fill="#f4ede4" font-size="16" font-weight="700">重要性</text>
    <text x="364" y="100" fill="#9a93a8" font-size="13">写入时打分</text>
    <text x="364" y="120" fill="#9a93a8" font-size="13">1 到 10</text>
    <text x="14" y="168" fill="#f4ede4" font-size="14" text-anchor="start">新鲜度曲线（本文代码：半衰期 30 天）</text>
    <line x1="60" y1="290" x2="404" y2="290" stroke="#9a93a8" stroke-width="1.5"/>
    <line x1="60" y1="290" x2="60" y2="184" stroke="#9a93a8" stroke-width="1.5"/>
    <line x1="60" y1="240" x2="173" y2="240" stroke="rgba(255,255,255,.18)" stroke-dasharray="4 4"/>
    <line x1="173" y1="240" x2="173" y2="290" stroke="rgba(255,255,255,.18)" stroke-dasharray="4 4"/>
    <polyline points="60,190 97.8,210.6 135.6,227 173.3,240 211.1,250.3 248.9,258.5 286.7,265 324.4,270.2 362.2,274.3 400,277.5" fill="none" stroke="#fcd5ce" stroke-width="3"/>
    <text x="52" y="195" fill="#9a93a8" font-size="13" text-anchor="end">1.0</text>
    <text x="52" y="245" fill="#9a93a8" font-size="13" text-anchor="end">0.5</text>
    <text x="60" y="310" fill="#9a93a8" font-size="13">0</text>
    <text x="173" y="310" fill="#9a93a8" font-size="13">30</text>
    <text x="287" y="310" fill="#9a93a8" font-size="13">60</text>
    <text x="392" y="310" fill="#9a93a8" font-size="13">90 天</text>
    <text x="186" y="224" fill="#fcd5ce" font-size="13" text-anchor="start">30 天后减半</text>
  </g>
</svg>
<figcaption>三项分数各自缩放到 0～1 后相加。新鲜度按时间指数衰减，记忆每被用到一次就重新变「新」</figcaption>
</figure>

只按语义相似度检索，很久以前的小事可能因为措辞相近排在最前，重要的记忆反而被挤出去。斯坦福大学等机构在 2023 年的论文 *Generative Agents: Interactive Simulacra of Human Behavior* 中，给小镇模拟里的 25 个 Agent 设计了一套检索打分，后来被大量借鉴：

- **相关性**（relevance）：用模型生成记忆文本和当前查询的 Embedding，计算余弦相似度；
- **新鲜度**（recency）：按「距离这条记忆**上次被检索**的游戏内小时数」做指数衰减，衰减因子是 0.995；
- **重要性**（importance）：记忆**创建时**让模型按 1～10 打分，提示词大意是「1 表示完全平常（比如刷牙、整理床铺），10 表示极其深刻（比如分手、被录取）」。论文里的例子：「打扫房间」得 2 分，「约暗恋对象出去」得 8 分。

三项分数用 min-max 方法各自缩放到 [0, 1]，再加权求和；论文的实现里三个权重都取 1。排名靠前、并且放得进上下文窗口的记忆被放进提示词。

注意两个细节：新鲜度看的是**上次被用到**而不是创建时间，常被想起的记忆一直保持新鲜；重要性只在写入时算一次，检索时不再调用模型。

实际系统还会加上：**硬过滤**（先按用户 ID、项目过滤再算分，用户 ID 绝不能只靠相似度）；**混合检索**（向量 + BM25，对专有名词更稳，见《RAG 是什么》）；**查询改写**（把「上次那个方案」改写成「限流方案 令牌桶」再检索）；**数量控制**（宁可少放，不要塞进无关记忆）。

### 更新与冲突：新事实覆盖旧事实

<figure>
<svg viewBox="0 0 440 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="记忆的冲突更新">
  <rect width="440" height="300" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="28" fill="#fcd5ce" font-size="17" font-weight="800">同一主题，新值覆盖旧值</text>
    <line x1="30" y1="62" x2="410" y2="62" stroke="#9a93a8" stroke-width="1.5"/>
    <circle cx="70" cy="62" r="6" fill="#9a93a8"/>
    <circle cx="220" cy="62" r="6" fill="#fcd5ce"/>
    <circle cx="364" cy="62" r="6" fill="#fcd5ce"/>
    <text x="70" y="90" fill="#9a93a8" font-size="13">第 0 天 说用 Go</text>
    <text x="220" y="90" fill="#fcd5ce" font-size="13">第 10 天 改用 Rust</text>
    <text x="364" y="90" fill="#9a93a8" font-size="13">第 45 天 问框架</text>
    <rect x="14" y="112" width="200" height="66" rx="12" fill="rgba(255,255,255,.03)" stroke="#9a93a8" stroke-dasharray="5 4"/>
    <text x="114" y="140" fill="#9a93a8" font-size="15" font-weight="700">user.lang = Go</text>
    <text x="114" y="164" fill="#9a93a8" font-size="13">第 0～10 天有效 · 历史</text>
    <rect x="226" y="112" width="200" height="66" rx="12" fill="rgba(252,213,206,.16)" stroke="#fcd5ce"/>
    <text x="326" y="140" fill="#fcd5ce" font-size="15" font-weight="800">user.lang = Rust</text>
    <text x="326" y="164" fill="#f4ede4" font-size="13">第 10 天起有效 · 当前</text>
    <text x="220" y="214" fill="#f4ede4" font-size="14">由模型选择的四种操作（Mem0 的做法）</text>
    <rect x="12" y="228" width="98" height="58" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="61" y="252" fill="#fcd5ce" font-size="15" font-weight="800">ADD</text>
    <text x="61" y="274" fill="#9a93a8" font-size="13">新增</text>
    <rect x="118" y="228" width="98" height="58" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="167" y="252" fill="#fcd5ce" font-size="15" font-weight="800">UPDATE</text>
    <text x="167" y="274" fill="#9a93a8" font-size="13">补充合并</text>
    <rect x="224" y="228" width="98" height="58" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="273" y="252" fill="#fcd5ce" font-size="15" font-weight="800">DELETE</text>
    <text x="273" y="274" fill="#9a93a8" font-size="13">删掉矛盾</text>
    <rect x="330" y="228" width="98" height="58" rx="10" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="379" y="252" fill="#fcd5ce" font-size="15" font-weight="800">NOOP</text>
    <text x="379" y="274" fill="#9a93a8" font-size="13">无需改动</text>
  </g>
</svg>
<figcaption>旧值不直接删除，而是标记为失效并保留有效期，既能回答「现在用什么」，也能回答「以前用什么」</figcaption>
</figure>

用户的情况会变。新旧两条记忆同时被检索出来，模型可能用旧的，也可能混在一起胡乱回答。所以写入不能只是追加，还要处理冲突：

| 策略 | 做法 | 适合 |
|---|---|---|
| **按 key 覆盖** | 同一个字段（如 `user.lang`）只保留最新值 | 结构化档案，字段事先定义好 |
| **覆盖但保留历史** | 旧值标记为失效、记下失效时间，新值指向它 | 需要回答「以前是什么」或需要审计的场景 |
| **双时间戳** | 每条记录同时有「事实生效时间」和「系统记录时间」 | 用户事后补充信息（「其实我上个月就换了」） |
| **交给模型判断** | 检索出相似的旧记忆，让模型决定增、改、删还是不动 | 自由文本记忆，无法事先定义字段 |

最后一种是 Mem0 论文（2025 年）的做法：对话产生新消息后，先由模型从「整段对话的摘要 + 最近若干条消息」里抽取候选事实；然后对每条候选事实，用向量检索找出最相似的若干条已有记忆，一起交给模型，通过函数调用选择四种操作之一：**ADD**（没有语义等价的记忆，新增）、**UPDATE**（补充已有记忆）、**DELETE**（新信息与旧记忆矛盾，删除旧的）、**NOOP**（不需要改动）。

交给模型判断的风险是**误判冲突**：「喜欢喝咖啡」和「晚上不喝咖啡」并不矛盾。误删比漏删更难发现，重要字段最好用结构化的 key 管理。

### 遗忘：过期、衰减、删除

会忘记是必要的能力：旧记忆越积越多会挤占检索结果；过时的信息比没有信息更有害；存储和检索成本随数量增长；用户也有权要求删除自己的数据。常见方式：

| 方式 | 做法 | 适合 |
|---|---|---|
| **TTL 过期** | 写入时设定有效期，到期删除 | 天然有时效的信息：「这周在出差」、会话摘要 |
| **衰减淘汰** | 按「重要性 × 新鲜度」计算记忆强度，低于阈值就删除或归档 | 大量低价值的事件记录 |
| **合并压缩** | 把多条旧事件合并成一条摘要，删除原文 | 情景记忆太多时 |
| **被覆盖** | 冲突更新后旧值失效 | 事实类记忆 |
| **用户要求删除** | 用户说「忘掉这个」，或在设置里删除 | 任何记忆，优先级最高 |

用户要求删除时要**删干净**：一条信息可能同时存在于聊天记录、抽取的事实、向量索引、摘要、缓存和备份里，漏掉一处就可能重新出现。主流产品对此有明确说明：OpenAI 的帮助文档写明，删除一段聊天**不一定**会删除从中产生的已保存记忆，要彻底移除需要分别删除；删除的已保存记忆，日志可能会为安全和调试目的保留最多 30 天。Claude 的帮助文档则说明，删除的对话会从记忆综合中移除，记忆会在对话变化后 24 小时内更新。

## 记忆与 RAG：同一套技术，不同的问题

| | RAG | Agent 记忆 |
|---|---|---|
| 数据从哪来 | 外部文档：手册、知识库、代码 | 与用户的交互：对话、行为、反馈 |
| 读写方式 | 以读为主，离线批量建索引 | 边用边写，每轮都可能产生新记忆 |
| 作用范围 | 通常所有用户共享 | 按用户（或项目、团队）隔离 |
| 冲突 | 文档有版本，一般由人维护 | 用户的话会前后矛盾，要自动处理 |
| 遗忘 | 文档下线即删除 | 需要过期、衰减、按用户要求删除 |
| 隐私 | 文档权限控制 | 个人信息，风险更高 |

联系也很紧密：按需检索的那部分记忆，本质上就是**对「关于这个用户的知识库」做 RAG**，Embedding、向量检索、重排序完全通用（见《Embedding 向量》）。Claude 帮助中心介绍「搜索过去的对话」时就直接说明它用的是 RAG。区别主要在写入侧：RAG 的知识库是人整理好放进去的，记忆是 Agent 在对话中自己积累的，所以要额外处理写什么、冲突和遗忘。

## 动手：用标准库写一个小型记忆系统

下面用 Python 标准库实现一个最小但完整的记忆系统：写入带类型、时间戳、重要性，并在存储层过滤敏感信息；带 key 的事实和规则常驻加载，事件按「相关性 + 新鲜度 + 重要性」检索（相关性用词袋余弦相似度代替 Embedding）；同一个 key 新值覆盖旧值并保留历史；遗忘包括 TTL 过期、衰减淘汰和按用户要求删除。

这里用一个**假模型**代替真实 LLM：`fake_extract` 用正则规则模拟「从对话中抽取记忆」，`fake_answer` 按规则拼出回答。换成真实 API 时，只需要替换这两个函数：前者改成一次要求输出 JSON 的模型调用（结构化输出见《Prompt 工程与结构化输出》），后者改成把「常驻档案 + 检索结果 + 会话历史」拼进 messages 调用模型。

先是记忆库本身：

```python
"""memory.py —— 一个只用标准库的小型 Agent 记忆系统"""
import json, math, re
from collections import Counter
from dataclasses import dataclass, asdict

HALF_LIFE_DAYS = 30            # 时间衰减：30 天没被用到，新鲜度减半

# 敏感信息过滤：命中就拒绝写入（真实系统还要更多规则，或交给专门的分类模型）
SENSITIVE = [
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "手机号"),
    (re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), "身份证号"),
    (re.compile(r"(?<!\d)\d{16,19}(?!\d)"), "银行卡号"),
    (re.compile(r"密码|password", re.I), "密码"),
]

def tokens(text):
    """极简分词：英文按单词，中文按相邻两个字（bigram）"""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    han = re.findall(r"[一-鿿]+", text)
    return words + [s[i:i + 2] for s in han for i in range(max(1, len(s) - 1))]

def cosine(a, b):
    """词袋向量的余弦相似度，代替真实的 Embedding"""
    va, vb = Counter(tokens(a)), Counter(tokens(b))
    dot = sum(va[t] * vb[t] for t in va)
    na = math.sqrt(sum(v * v for v in va.values()))
    nb = math.sqrt(sum(v * v for v in vb.values()))
    return dot / (na * nb) if na and nb else 0.0

@dataclass
class Memory:
    id: int
    kind: str                  # semantic 事实 / episodic 事件 / procedural 做事方法
    text: str                  # 写进 prompt 的那句话
    importance: int            # 1~10，由模型或规则打分
    created: float             # 时间都用「小时」表示，方便演示
    last_access: float
    key: str | None = None     # 有 key 的事实可以被新值覆盖，如 user.lang
    ttl_hours: float | None = None
    active: bool = True        # 被覆盖后变成 False，但保留做历史
    superseded_by: int | None = None

class MemoryStore:
    def __init__(self, path):
        self.path, self.items, self.log = path, [], []
        try:
            with open(path, encoding="utf-8") as f:
                self.items = [Memory(**m) for m in json.load(f)]
        except FileNotFoundError:
            pass

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in self.items], f, ensure_ascii=False, indent=1)

    # ---------- 写入：过滤敏感信息 + 冲突更新 ----------
    def write(self, kind, text, importance, now, key=None, ttl_hours=None):
        for pattern, name in SENSITIVE:
            if pattern.search(text):
                self.log.append(f"拒绝写入（含{name}）：{pattern.sub('***', text)}")
                return None
        old = next((m for m in self.items if m.active and m.key and m.key == key), None)
        if old and old.text == text:               # 重复信息：只刷新访问时间
            old.last_access = now
            return old
        next_id = max((m.id for m in self.items), default=0) + 1
        new = Memory(next_id, kind, text, importance, now, now, key, ttl_hours)
        self.items.append(new)
        if old:                                    # 同一主题的新值覆盖旧值，旧值留作历史
            old.active, old.superseded_by = False, new.id
            self.log.append(f"更新 {key}：「{old.text}」→「{text}」")
        else:
            self.log.append(f"新增 [{kind}] {text}")
        return new

    # ---------- 读取：常驻档案 + 按需检索 ----------
    def profile(self):
        """有 key 的事实和规则：条数少、每次都要用，直接常驻 prompt"""
        return [m for m in self.items if m.active and m.key]

    def recency(self, m, now):
        return 0.5 ** ((now - m.last_access) / 24 / HALF_LIFE_DAYS)

    def search(self, query, now, k=3, explain=False):
        cands = [m for m in self.items if m.active and not m.key]  # 只在事件里检索
        if not cands:
            return []
        raw = {"rel": [cosine(query, m.text) for m in cands],
               "rec": [self.recency(m, now) for m in cands],
               "imp": [m.importance for m in cands]}
        def minmax(xs):                            # 三项各自缩放到 [0,1] 再相加
            lo, hi = min(xs), max(xs)
            return [(x - lo) / (hi - lo) if hi > lo else 0.0 for x in xs]
        norm = {name: minmax(xs) for name, xs in raw.items()}
        rows = []
        for i, m in enumerate(cands):
            score = norm["rel"][i] + norm["rec"][i] + norm["imp"][i]
            if raw["rel"][i] == 0:                 # 和问题毫无关系的不召回
                score = 0.0
            rows.append((score, m, raw["rel"][i], raw["rec"][i]))
        rows.sort(key=lambda r: -r[0])
        if explain:
            print(f"  {'总分':>4} {'相关':>5} {'新鲜':>5} {'重要':>3}  记忆")
            for score, m, rel, rec in rows:
                print(f"  {score:4.2f} {rel:5.2f} {rec:5.2f} {m.importance:3d}  {m.text}")
        hits = [m for score, m, _, _ in rows[:k] if score > 0]
        for m in hits:
            m.last_access = now                    # 被用到的记忆「变新鲜」
        return hits

    # ---------- 遗忘：过期、衰减、用户要求删除 ----------
    def forget(self, now, min_strength=1.0):
        keep = []
        for m in self.items:
            strength = m.importance * self.recency(m, now)
            if m.ttl_hours is not None and now - m.created > m.ttl_hours:
                self.log.append(f"过期删除：{m.text}")
            elif m.kind == "episodic" and strength < min_strength:
                self.log.append(f"衰减删除（强度 {strength:.2f}）：{m.text}")
            else:
                keep.append(m)
        self.items = keep

    def forget_about(self, key_prefix):
        """用户说「忘掉」：连同历史版本一起硬删除"""
        gone = [m for m in self.items if m.key and m.key.startswith(key_prefix)]
        self.items = [m for m in self.items if m not in gone]
        self.log.append(f"按用户要求删除 {len(gone)} 条（含历史版本）：{key_prefix}*")

    def history(self, key):
        return [(m.text, "当前" if m.active else "已被覆盖") for m in self.items if m.key == key]
```

几个设计选择：新鲜度用**半衰期 30 天**而不是论文的「每游戏小时 × 0.995」，因为真实用户的时间尺度是周和月；**只有事件参与检索**，事实和规则全部常驻；**衰减淘汰只作用于情景记忆**，否则用户两个月没提自己的名字，名字就会被「忘掉」。

然后是 Agent 和四次会话。每次会话都新建一个 `Agent` 对象，模拟「模型无状态、新会话一片空白」，唯一跨会话保留的是 `memory.json` 文件：

```python
"""agent_demo.py —— 用假模型演示：跨会话记住用户偏好"""
import os, re
from memory import MemoryStore

DAY = 24  # 记忆系统里的时间单位是小时

# ===== 假模型：代替真实 LLM。换成真实 API 只需替换这两个函数 =====
def fake_extract(message):
    """「记忆抽取」调用：真实系统里是一次 LLM 调用，返回 JSON 操作列表"""
    ops = []
    if m := re.search(r"我叫(\w+?)[，,。]", message):
        ops.append({"kind": "semantic", "key": "user.name", "text": f"用户名叫{m[1]}", "importance": 8})
    if m := re.search(r"是一名(\w+?工程师)", message):
        ops.append({"kind": "semantic", "key": "user.role", "text": f"用户是{m[1]}", "importance": 6})
    if m := re.search(r"(?:平时用|改用)\s*([A-Za-z]+)", message):
        ops.append({"kind": "semantic", "key": "user.lang", "text": f"用户的主力编程语言是 {m[1]}", "importance": 7})
    if "简短" in message or "先给结论" in message:
        ops.append({"kind": "procedural", "key": "style.answer", "text": "回答规则：先给结论，控制在两三句", "importance": 9})
    if "手机号" in message:  # 模型「以为」该记；交给存储层的过滤器拦下
        ops.append({"kind": "semantic", "key": "user.phone", "text": message, "importance": 5})
    if "被刷" in message:
        ops.append({"kind": "episodic", "text": "用户提到登录接口上周被刷过一次", "importance": 6})
    if "有点累" in message:
        ops.append({"kind": "episodic", "text": "用户说今天在赶需求，有点累", "importance": 2})
    if m := re.search(r"忘掉我的(职业|名字|语言)", message):
        ops.append({"forget": {"职业": "user.role", "名字": "user.name", "语言": "user.lang"}[m[1]]})
    return ops

def fake_answer(question, prompt_parts):
    """「回答」调用：prompt_parts = 常驻档案 + 检索到的记忆 + 本次会话的历史消息"""
    mem = " ".join(prompt_parts)
    lang = re.findall(r"主力编程语言是 (\w+)", mem)
    lang = lang[-1] if lang else None
    if "手机号" in question:
        ans = "手机号属于敏感信息，我不会把它存进长期记忆。"
    elif "熔断" in question:
        ans = "在限流外面再包一层熔断器：错误率超过阈值就快速失败，冷却后半开试探。"
        if "限流" in mem:
            ans = "接着上次的令牌桶方案，" + ans
    elif "限流" in question:
        ans = "用令牌桶：桶按固定速率补充令牌，请求拿到令牌才放行。"
        if lang == "Go":
            ans += "Go 里可以直接用 golang.org/x/time/rate。"
    elif "忘掉" in question:
        ans = "好的，已删除相关记忆。"
    elif "HTTP" in question:
        ans = {"Go": "标准库 net/http 就够用。", "Rust": "可以用 axum 或 actix-web。"}.get(lang, "你用什么语言？")
    else:
        name = re.search(r"我叫(\w+?)[，,]|用户名叫(\w+)", mem)
        ans = f"好的{'，' + (name[1] or name[2]) if name else ''}，记下了。"
    if "先给结论" in mem:                           # 有风格偏好 → 简短
        return "结论：" + ans
    return "这是个好问题，我们先从背景讲起……" + ans   # 没有 → 啰嗦的默认风格

# ===== Agent：模型本身无状态，每次会话都从记忆库「重新认识」用户 =====
class Agent:
    def __init__(self, store_path, now, use_memory=True):
        self.store = MemoryStore(store_path) if use_memory else None
        self.context = []                           # 短期记忆：本次会话的消息
        self.now = now
        self.pinned = []
        if self.store:
            self.store.forget(now)                  # 每次加载时顺手做遗忘
            self.pinned = [m.text for m in self.store.profile()]
            print(f"    · 常驻档案 {len(self.pinned)} 条：{'；'.join(self.pinned) or '（空）'}")

    def chat(self, message, explain=False):
        self.context.append(message)
        hits = self.store.search(message, self.now, k=2, explain=explain) if self.store else []
        print(f"用户：{message}")
        for m in hits:
            print(f"    · 检索到：{m.text}")
        # 真实系统里：system prompt + 档案 + 检索结果 + 会话历史，一起发给模型
        reply = fake_answer(message, self.pinned + [m.text for m in hits] + self.context)
        self.context.append(reply)
        print(f"助手：{reply}")
        if self.store:                              # 回答之后，再做一次记忆抽取
            for op in fake_extract(message):
                if "forget" in op:
                    self.store.forget_about(op["forget"])
                else:
                    self.store.write(now=self.now, **op)

    def end_session(self, summary):
        if self.store:                              # 会话摘要作为情景记忆，30 天后过期
            self.store.write("episodic", summary, 4, self.now, ttl_hours=30 * DAY)
            self.store.save()
            for line in self.store.log:
                print(f"  [记忆] {line}")

PATH = "memory.json"
if os.path.exists(PATH):
    os.remove(PATH)

print("===== 会话 1（第 0 天）=====")
a = Agent(PATH, now=0)
a.chat("你好，我叫小林，是一名后端工程师，平时用 Go。")
a.chat("以后回答尽量简短，先给结论。")
a.chat("我的手机号是 13812345678，你帮我记一下。")
a.end_session("第 1 次会话：自我介绍，约定了回答风格")

print("\n===== 会话 2（第 3 天）：对照组，不带记忆 =====")
Agent(PATH, now=3 * DAY, use_memory=False).chat("帮我设计一个接口限流方案")

print("\n===== 会话 2（第 3 天）：带记忆 =====")
a = Agent(PATH, now=3 * DAY)
a.chat("帮我设计一个接口限流方案")
a.chat("顺便说下，登录接口上周被刷过一次。")
a.chat("今天在赶需求，有点累。")
a.end_session("第 2 次会话：讨论了接口限流方案（令牌桶）")

print("\n===== 会话 3（第 10 天）=====")
a = Agent(PATH, now=10 * DAY)
a.chat("上次说的接口限流方案，再加个熔断要怎么做？", explain=True)
a.chat("另外我最近改用 Rust 了。")
a.end_session("第 3 次会话：讨论了熔断")

print("\n===== 会话 4（第 45 天）=====")
a = Agent(PATH, now=45 * DAY)
a.chat("写个 HTTP 服务用什么框架？")
a.chat("忘掉我的职业信息。")
a.end_session("第 4 次会话：讨论了 HTTP 框架")

print("\n===== user.lang 的历史版本 =====")
for text, state in a.store.history("user.lang"):
    print(f"  {state}：{text}")
print("\n===== 最终记忆库 =====")
for m in a.store.items:
    flag = "" if m.active else "（历史）"
    print(f"  #{m.id} [{m.kind}] {m.text} 重要性={m.importance}{flag}")
```

把两个文件放在同一目录，运行 `python3 agent_demo.py`，输出（Python 3.13，结果是确定的）：

```text
===== 会话 1（第 0 天）=====
    · 常驻档案 0 条：（空）
用户：你好，我叫小林，是一名后端工程师，平时用 Go。
助手：这是个好问题，我们先从背景讲起……好的，小林，记下了。
用户：以后回答尽量简短，先给结论。
助手：结论：好的，小林，记下了。
用户：我的手机号是 13812345678，你帮我记一下。
助手：结论：手机号属于敏感信息，我不会把它存进长期记忆。
  [记忆] 新增 [semantic] 用户名叫小林
  [记忆] 新增 [semantic] 用户是后端工程师
  [记忆] 新增 [semantic] 用户的主力编程语言是 Go
  [记忆] 新增 [procedural] 回答规则：先给结论，控制在两三句
  [记忆] 拒绝写入（含手机号）：我的手机号是 ***，你帮我记一下。
  [记忆] 新增 [episodic] 第 1 次会话：自我介绍，约定了回答风格

===== 会话 2（第 3 天）：对照组，不带记忆 =====
用户：帮我设计一个接口限流方案
助手：这是个好问题，我们先从背景讲起……用令牌桶：桶按固定速率补充令牌，请求拿到令牌才放行。

===== 会话 2（第 3 天）：带记忆 =====
    · 常驻档案 4 条：用户名叫小林；用户是后端工程师；用户的主力编程语言是 Go；回答规则：先给结论，控制在两三句
用户：帮我设计一个接口限流方案
助手：结论：用令牌桶：桶按固定速率补充令牌，请求拿到令牌才放行。Go 里可以直接用 golang.org/x/time/rate。
用户：顺便说下，登录接口上周被刷过一次。
助手：结论：好的，小林，记下了。
用户：今天在赶需求，有点累。
助手：结论：好的，小林，记下了。
  [记忆] 新增 [episodic] 用户提到登录接口上周被刷过一次
  [记忆] 新增 [episodic] 用户说今天在赶需求，有点累
  [记忆] 新增 [episodic] 第 2 次会话：讨论了接口限流方案（令牌桶）

===== 会话 3（第 10 天）=====
    · 常驻档案 4 条：用户名叫小林；用户是后端工程师；用户的主力编程语言是 Go；回答规则：先给结论，控制在两三句
    总分    相关    新鲜  重要  记忆
  2.50  0.34  0.85   4  第 2 次会话：讨论了接口限流方案（令牌桶）
  2.19  0.06  0.85   6  用户提到登录接口上周被刷过一次
  0.00  0.00  0.79   4  第 1 次会话：自我介绍，约定了回答风格
  0.00  0.00  0.85   2  用户说今天在赶需求，有点累
用户：上次说的接口限流方案，再加个熔断要怎么做？
    · 检索到：第 2 次会话：讨论了接口限流方案（令牌桶）
    · 检索到：用户提到登录接口上周被刷过一次
助手：结论：接着上次的令牌桶方案，在限流外面再包一层熔断器：错误率超过阈值就快速失败，冷却后半开试探。
用户：另外我最近改用 Rust 了。
助手：结论：好的，小林，记下了。
  [记忆] 更新 user.lang：「用户的主力编程语言是 Go」→「用户的主力编程语言是 Rust」
  [记忆] 新增 [episodic] 第 3 次会话：讨论了熔断

===== 会话 4（第 45 天）=====
    · 常驻档案 4 条：用户名叫小林；用户是后端工程师；回答规则：先给结论，控制在两三句；用户的主力编程语言是 Rust
用户：写个 HTTP 服务用什么框架？
助手：结论：可以用 axum 或 actix-web。
用户：忘掉我的职业信息。
助手：结论：好的，已删除相关记忆。
  [记忆] 过期删除：第 1 次会话：自我介绍，约定了回答风格
  [记忆] 衰减删除（强度 0.76）：用户说今天在赶需求，有点累
  [记忆] 过期删除：第 2 次会话：讨论了接口限流方案（令牌桶）
  [记忆] 过期删除：第 3 次会话：讨论了熔断
  [记忆] 按用户要求删除 1 条（含历史版本）：user.role*
  [记忆] 新增 [episodic] 第 4 次会话：讨论了 HTTP 框架

===== user.lang 的历史版本 =====
  已被覆盖：用户的主力编程语言是 Go
  当前：用户的主力编程语言是 Rust

===== 最终记忆库 =====
  #1 [semantic] 用户名叫小林 重要性=8
  #3 [semantic] 用户的主力编程语言是 Go 重要性=7（历史）
  #4 [procedural] 回答规则：先给结论，控制在两三句 重要性=9
  #6 [episodic] 用户提到登录接口上周被刷过一次 重要性=6
  #9 [semantic] 用户的主力编程语言是 Rust 重要性=7
  #10 [episodic] 第 4 次会话：讨论了 HTTP 框架 重要性=4
```

逐段看：

- **短期记忆**：会话 1 第二句之后回答就变成「结论：……」，这时长期记忆还是空的，靠的是本次会话的上下文；
- **敏感信息过滤**：假模型「以为」手机号该记，被存储层的规则拦下。过滤不能只靠模型自觉；
- **对照组**：不带记忆的 Agent 用默认的啰嗦风格，也不知道用户用 Go；
- **检索打分**：会话 3 的打分表里，「第 2 次会话」相关性最高（0.34）；「登录接口被刷」相关性只有 0.06，但重要性是 6（候选里最高），总分 2.19 排第二；两条与问题毫无关系的记忆被直接排除。可以手算一下：相关性缩放后分别是 1 和 0.065 / 0.336 ≈ 0.19（表里显示的是保留两位的值），新鲜度都是最大值 1，重要性缩放后分别是 (4 − 2) / (6 − 2) = 0.5 和 1，加起来正是 2.50 和 2.19；
- **冲突更新**：「改用 Rust」覆盖了「Go」，会话 4 给的是 Rust 的答案，旧值仍可通过 `history` 查到；
- **三种遗忘**：会话摘要 30 天 TTL 到期；「有点累」重要性 2、42 天没被用到，强度 2 × 0.5^(42/30) ≈ 0.76，低于阈值 1 被淘汰；「登录接口被刷」重要性 6，又在第 10 天被检索过（刷新了新鲜度），留了下来；职业信息按用户要求硬删除。

离生产还很远：词袋不懂同义词，正则会漏掉很多敏感信息，JSON 文件不支持并发写。但骨架都在，换成 Embedding、向量库和真实模型调用，结构不用变。

## 主流产品与框架怎么做

各家的具体功能、套餐范围和界面变化很快，下面只列官方文档中能核实的设计要点，细节以各自最新文档为准。

| 产品 / 框架 | 常驻部分 | 检索部分 | 谁来写 | 用户控制 |
|---|---|---|---|---|
| ChatGPT | 已保存的记忆 | 引用聊天记录 | 用户要求或模型判断有用时 | 查看、删除、关闭，临时聊天 |
| Claude 应用 | 记忆摘要（按项目隔离） | 搜索过去的对话（RAG） | 后台定期综合 | 查看编辑、暂停、重置，无痕聊天 |
| Claude API memory tool | 由应用决定 | 模型浏览 `/memories` 目录 | 模型主动调用工具 | 存储完全由开发者控制 |
| Claude Code | CLAUDE.md、MEMORY.md 索引 | 按需读取主题文件 | 人写 CLAUDE.md，模型写 auto memory | 文件可直接编辑、可关闭 |
| MemGPT / Letta | working context（记忆块） | recall / archival 存储 | 模型通过函数调用编辑 | 由开发者实现 |

### ChatGPT

OpenAI 在 2024 年 2 月发布 ChatGPT 记忆功能，2025 年 4 月扩展为可引用过去的所有对话。按帮助中心的说明，它分为**已保存的记忆**（用户要求记住或模型认为有用的内容，与聊天记录分开存放）和**引用聊天记录**（动态使用相关的过去对话）。用户可在个性化设置中查看和删除，临时聊天不会创建或更新记忆。发布公告还提到，会引导 ChatGPT 不主动记住健康等敏感信息，除非用户明确要求。

### Claude 应用与 Claude API

Claude 帮助中心描述了两个功能：**搜索和引用过去的对话**（付费套餐），基于 RAG，搜索以工具调用的形式显示；**基于聊天记录的记忆**，从非项目对话中综合出记忆摘要，每 24 小时更新，每个项目有独立、隔离的记忆空间。用户可以查看编辑、暂停或重置记忆，也可以用不进入记忆的无痕聊天。

面向开发者，Claude API 提供 **memory tool**（工具类型 `memory_20250818`）。它是**客户端工具**：模型只发出 `view`、`create`、`str_replace`、`insert`、`delete`、`rename` 等对 `/memories` 目录的操作请求，实际读写由你的应用执行，存在哪里由你决定。官方文档强调要防范**路径穿越**：路径必须以 `/memories` 开头，解析后确认仍在记忆目录内，拒绝 `../` 及其 URL 编码形式。参考写法（未实际运行，需要 API Key）：

```python
# 参考写法：在请求里声明 memory tool，模型返回 tool_use 后由你的代码执行文件操作
tools = [{"type": "memory_20250818", "name": "memory"}]
# 收到 {"command": "view", "path": "/memories"} 之类的请求时：
#   1. 校验 path 以 /memories 开头，resolve 之后仍在你的记忆目录内
#   2. 映射到当前用户自己的目录，执行操作
#   3. 把结果放进 tool_result 返回给模型
```

### Claude Code：文件式记忆

Claude Code 是「文件即记忆」的典型。按官方文档，它有两套机制，都在会话开始时加载：

- **CLAUDE.md**：人写的指令和规则，分组织级、用户级（`~/.claude/CLAUDE.md`）、项目级（可提交到 git 与团队共享）和本地（`CLAUDE.local.md`，不提交），可用 `@路径` 导入其他文件。官方建议每个文件控制在 200 行以内；
- **auto memory**：Claude 自己写的笔记，位于 `~/.claude/projects/<项目>/memory/`，由 `MEMORY.md` 索引和若干主题文件组成。每次加载索引的前 200 行或 25KB，主题文件按需读取。

好处是**透明**：记忆就是 Markdown 文件，可以直接打开、修改、删除、纳入版本控制。「短索引常驻 + 细节按需读取」也正是前面讲的分层思路。

### MemGPT 与 Letta

2023 年的论文 *MemGPT: Towards LLMs as Operating Systems* 借用了操作系统虚拟内存的思路：上下文窗口是内存，外部存储是磁盘，模型自己通过函数调用在两者之间搬运数据。上下文分三段：只读的**系统指令**；固定大小、只能通过函数调用修改的 **working context**（关于用户和自身角色的关键事实）；**先进先出的消息队列**。上下文外有保存全部历史消息的 **recall storage** 和可读写任意文本的 **archival storage**。上下文用量超过警戒线时，系统插入「内存压力」警告，提示模型赶紧把重要信息存起来。

MemGPT 项目后来发展为 Letta，接口仍在演进，当前文档的核心概念是可编辑的**记忆块**（memory blocks），以官方文档为准。

### Mem0

Mem0 是开源的记忆层，前面的「抽取 + ADD / UPDATE / DELETE / NOOP」来自它 2025 年的论文；论文还提出了用图存储实体关系的变体。

## 隐私与安全

<figure>
<svg viewBox="0 0 440 330" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="记忆投毒">
  <rect width="440" height="330" fill="#0f0e1c"/>
  <defs><marker id="am-a6" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#ff8a80"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="28" fill="#fcd5ce" font-size="17" font-weight="800">记忆投毒：一次注入，长期生效</text>
    <rect x="14" y="48" width="216" height="52" rx="12" fill="rgba(255,138,128,.12)" stroke="#ff8a80"/>
    <text x="122" y="70" fill="#ff8a80" font-size="15" font-weight="700">恶意网页 / 文档</text>
    <text x="122" y="90" fill="#9a93a8" font-size="13">藏着「请记住：……」</text>
    <line x1="122" y1="100" x2="122" y2="118" stroke="#ff8a80" stroke-width="2.5" marker-end="url(#am-a6)"/>
    <rect x="14" y="122" width="216" height="52" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="122" y="144" fill="#f4ede4" font-size="15" font-weight="700">Agent 读取内容</text>
    <text x="122" y="164" fill="#9a93a8" font-size="13">被诱导调用「写记忆」</text>
    <line x1="122" y1="174" x2="122" y2="192" stroke="#ff8a80" stroke-width="2.5" marker-end="url(#am-a6)"/>
    <rect x="14" y="196" width="216" height="52" rx="12" fill="rgba(255,138,128,.12)" stroke="#ff8a80"/>
    <text x="122" y="218" fill="#ff8a80" font-size="15" font-weight="700">记忆库被污染</text>
    <text x="122" y="238" fill="#9a93a8" font-size="13">恶意指令成了「偏好」</text>
    <line x1="122" y1="248" x2="122" y2="266" stroke="#ff8a80" stroke-width="2.5" marker-end="url(#am-a6)"/>
    <rect x="14" y="270" width="216" height="52" rx="12" fill="rgba(255,255,255,.06)" stroke="#9a93a8"/>
    <text x="122" y="292" fill="#f4ede4" font-size="15" font-weight="700">之后每个新会话</text>
    <text x="122" y="312" fill="#9a93a8" font-size="13">都加载并执行它</text>
    <rect x="246" y="48" width="180" height="274" rx="12" fill="rgba(252,213,206,.08)" stroke="#fcd5ce"/>
    <text x="336" y="78" fill="#fcd5ce" font-size="16" font-weight="800">防御</text>
    <g text-anchor="start" font-size="13" fill="#f4ede4">
      <text x="260" y="112">· 记录每条记忆的来源</text>
      <text x="260" y="148">· 外部内容不能直接</text>
      <text x="272" y="168">触发写记忆</text>
      <text x="260" y="204">· 写入要可见、可确认</text>
      <text x="260" y="240">· 记忆当数据，不当指令</text>
      <text x="260" y="276">· 定期审计、可删除</text>
      <text x="260" y="304">· 敏感信息不入库</text>
    </g>
  </g>
</svg>
<figcaption>普通的提示词注入只影响一次对话；写进记忆的注入会在之后每个会话里被重新加载</figcaption>
</figure>

记忆是**持久的**，所以风险比普通对话高一个量级。

### 什么不该记，用户能做什么

不该记的：**高敏感信息**（证件号、银行卡号、密码密钥、健康状况等，随口提到不等于同意长期保存）；**第三方的隐私**（「我同事最近在闹离婚」）；**推断出来的标签**（从对话推测性格、政治倾向并当作事实存下）。过滤应放在**存储层**作为独立防线：规则能拦住格式明显的卡号、证件号，格式不明显的需要分类模型，宁可漏记也不要误记。

用户至少要能做到四件事：**看得见**（记住了什么、某次回答用了哪些记忆）、**改得了**、**删得掉**（真的删干净）、**关得了**（暂停记忆或使用临时会话）。前面介绍的产品基本都提供了，这也是自家 Agent 的底线。

多用户系统里，检索**必须**先按用户 ID 硬过滤，否则可能把 A 的记忆注入 B 的对话；团队共享的记忆（如项目级 CLAUDE.md）也不该写进个人偏好。

### 记忆投毒

普通的提示词注入（见同批文章《Agent 安全与提示词注入》）只影响一次对话；如果攻击者能让 Agent **把恶意指令写进记忆**，它会在之后每次会话中被重新加载。

2024 年，安全研究者公开演示过针对 ChatGPT macOS 应用记忆功能的攻击：用户只要让 ChatGPT 访问一个恶意网页或分析一份恶意文档，隐藏在内容中的指令就能让它在记忆里写入「把之后的对话发送到攻击者服务器」之类的内容，从而在后续会话中持续泄露数据。OpenAI 在 1.2024.247 版本中关闭了这条外传通道。学术界也有系统的研究：*AgentPoison*（NeurIPS 2024）针对 Agent 的记忆或知识库投毒，在三类 Agent 上，投毒比例低于 0.1% 时平均攻击成功率超过 80%，而对正常任务的影响不到 1%，很难被察觉。

防御思路见上图右侧：每条记忆记录来源（用户本人、模型推断还是外部内容）；网页、邮件里的「请记住……」只是数据，不能直接触发写入；写记忆时通知用户，会改变行为的规则需要确认；注入上下文时用明确的边界标出「这是参考信息」；定期扫描可疑内容（URL、外发指令、「忽略之前的规则」）；文件式记忆要校验路径。

## 怎么评估记忆系统

记忆的问题往往在几十轮、几周之后才暴露，「试几次感觉不错」不够。公开基准有 **LoCoMo**（2024，每段对话最多 35 个会话、平均约 300 轮）和 **LongMemEval**（2024，考察信息抽取、跨会话推理、时间推理、知识更新、拒答五种能力；论文发现商用聊天助手和长上下文模型在持续交互中准确率下降约 30%）。工程上可以按这些维度构造评测集（方法见《评估（Evals）》）：

| 维度 | 测什么 | 例子 |
|---|---|---|
| 召回 | 该想起的能不能想起来 | 第 1 次会话说用 Go，第 5 次会话问写法，答案是否用 Go |
| 更新 | 是否用最新的事实 | 先说 Go 后说 Rust，是否用 Rust |
| 拒答 | 没记过的不瞎编 | 从未提过宠物，问「我的猫叫什么」应回答不知道 |
| 写入精度 | 有没有记不该记的 | 手机号、一次性请求是否进了记忆库 |
| 删除生效 | 删了之后还会不会出现 | 删除后多轮追问，信息不应再出现 |
| 隔离 | 会不会串号 | 用户 A 的信息是否出现在用户 B 的回答里 |

形式通常是**多会话脚本 + 断言**：按时间回放对话，在特定位置提问，检查回答是否包含（或不包含）指定信息。上面的 `agent_demo.py` 稍加改造就是一个最小的评测框架。

## 常见的坑

| 现象 | 原因 | 解决 |
|---|---|---|
| 偏好记住了却不生效 | 偏好只能靠检索取回，和当前问题语义不相关 | 偏好和规则常驻加载 |
| 用了过时的信息 | 新旧事实同时存在，没有冲突处理 | 按 key 覆盖或让模型判断更新，旧值标记失效 |
| 记忆越用越乱 | 什么都记，大量低价值记忆干扰检索 | 写入设门槛，配合 TTL 和衰减淘汰 |
| 用户说删了还会出现 | 只删了一处，摘要、向量索引、缓存里还有 | 删除要覆盖所有派生数据 |
| 每轮都变慢 | 每轮同步做抽取、更新 | 抽取异步化，只有明确的「记住」走同步 |
| 常驻记忆越来越长 | 档案不断追加，从不整理 | 控制常驻部分的大小，定期合并整理 |

## 高频面试题速答

**Q：大模型本身有记忆吗？对话为什么能「记得」上文？**
没有。模型调用是无状态的，同一对话里「记得」上文，是因为客户端每次都把历史消息整段发过去；跨对话的记忆需要在模型外部存储，并在下一次调用时放回上下文。

**Q：短期记忆和长期记忆分别是什么？长期记忆有哪几类？**
短期记忆是上下文窗口里的内容，会话结束即消失；长期记忆存在外部，跨会话保留，通过常驻加载或检索进入上下文。长期记忆分语义（事实与偏好）、情景（带时间的事件）、程序（方法与规则）三类。

**Q：记忆检索除了向量相似度还要考虑什么？**
新鲜度和重要性。Generative Agents 论文把相关性、新鲜度（按上次被检索以来的时间指数衰减）、重要性（写入时由模型打 1～10 分）分别归一化后加权求和。此外还要按用户 ID 硬过滤，并对偏好类信息常驻加载而不是检索。

**Q：新旧记忆冲突怎么处理？**
结构化字段按 key 覆盖，旧值标记失效并保留有效期；自由文本可以检索出相似的旧记忆，让模型选择新增、更新、删除或不动（如 Mem0 的做法）。要警惕误判冲突导致误删。

**Q：Agent 记忆和 RAG 有什么区别？**
技术栈相似，都可以用 Embedding 和向量检索。区别在于：RAG 的数据来自外部文档、以读为主、通常共享；记忆来自用户交互、边用边写、按用户隔离，需要额外处理写什么、冲突和遗忘。

**Q：记忆系统有哪些安全风险？**
敏感信息被长期保存；多用户检索没有隔离导致串号；记忆投毒，即外部内容通过提示词注入把恶意指令写进记忆，在之后每个会话中持续生效。防御包括来源标记、外部内容不能直接触发写入、写入可见、记忆当数据而非指令、用户可查看可删除。

**Q：怎么评估一个记忆系统？**
用多会话脚本回放对话，测召回、更新、拒答、写入精度、删除是否生效、用户隔离和额外成本。公开基准有 LoCoMo、LongMemEval。

## 总结

- **模型是无状态的**，记忆是模型外面的一套工程，核心是决定「下一次调用往上下文里放什么」；
- **分层**：短期记忆在上下文窗口里；长期记忆在外部，分为**常驻加载**和**按需检索**两种读取方式，偏好和规则应当常驻；
- **三种类型**：语义记忆（事实与偏好）、情景记忆（事件）、程序记忆（方法与规则）；
- **生命周期**：写入（何时、写什么、谁来写）→ 存储（文件、键值、向量、图）→ 检索（相关性 + 新鲜度 + 重要性）→ 更新（新值覆盖旧值，保留历史）→ 遗忘（过期、衰减、按要求删除）；
- **与 RAG**：检索技术相通，但记忆要自己写入、处理冲突、按用户隔离；
- **隐私与安全**：敏感信息不入库，用户可见可删，严格隔离，警惕记忆投毒。

好的记忆系统不是记得越多越好，而是在需要的时候想起对的事，在该忘的时候真的忘掉。

<div class="refs" markdown="1">

### 参考资料

- Park, J. S., et al. (2023). Generative Agents: Interactive Simulacra of Human Behavior. *UIST 2023*. arXiv:2304.03442.
- Packer, C., et al. (2023). MemGPT: Towards LLMs as Operating Systems. arXiv:2310.08560.
- Sumers, T. R., et al. (2023). Cognitive Architectures for Language Agents. *TMLR*. arXiv:2309.02427.
- Chhikara, P., et al. (2025). Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory. arXiv:2504.19413.
- Maharana, A., et al. (2024). Evaluating Very Long-Term Conversational Memory of LLM Agents (LoCoMo). arXiv:2402.17753.
- Wu, D., et al. (2024). LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory. arXiv:2410.10813.
- Chen, Z., et al. (2024). AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases. *NeurIPS 2024*. arXiv:2407.12784.
- OpenAI (2024). Memory and new controls for ChatGPT；OpenAI Help Center: Memory FAQ.
- Anthropic. Claude Help Center: Using memory / Search and reference past chats；Claude Docs: Memory tool；Claude Code Docs: How Claude remembers your project.
- Letta Docs: Memory blocks；Letta Blog: MemGPT and Letta.

</div>
