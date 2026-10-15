title: Skills 技能包：给 Agent 一本按需翻阅的操作手册
subtitle: 为什么不能把所有说明都写进系统提示，Skill 的文件夹结构与 SKILL.md 格式，渐进式披露的三层加载，和提示词、工具、MCP、子 Agent 的分工，写好一个 Skill 的方法，组织、版本与团队共享，安全风险，各家产品的类似机制，附一个可运行的迷你 Skill 加载器
tag: AI 与大模型
color: #f5d0fe

## 一份越写越长的系统提示

一个团队给内部的编程 Agent 写系统提示。第一版只有二十行：你是谁、回答要简洁、改代码前先跑测试。

后来需求一条条加进来。有人希望它会写周报，于是加了一段周报格式；DBA 希望它审 SQL 时遵守团队规范，于是贴进来一页 SQL 规范；数据组加了 CSV 清洗规则，运维加了发版检查清单，还有事故复盘模板、接口命名约定、日志字段说明……半年后，这份系统提示有三千多行。

接着问题出现了：

- 每次请求都要带上这三千行。用户只是问一句「这个函数什么意思」，也要为周报格式和发版清单付钱；
- Agent 写周报时，偶尔用上了 SQL 规范里的「按严重程度分三级」；
- 两条规则写在不同段落，互相矛盾，没有人发现；
- 谁都可以往里加内容，没有人敢删。

问题不在于这些说明写得不好，而在于它们**全部、每一次**都被塞进了上下文。人类员工也不会把公司所有的操作手册背下来，他们知道有哪些手册，遇到具体任务时再去翻对应的那一本。

**Skills（技能包）** 就是按这个思路设计的：给 Agent 一个书架，平时只看书脊上的标题，需要时再翻开具体某一本。

## 为什么不能都写进系统提示

<figure>
<svg viewBox="0 0 440 400" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="全部写进系统提示与按需加载的对比">
  <rect width="440" height="400" fill="#0f0e1c"/>
  <defs><marker id="sk-a1" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#f5d0fe"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="30" fill="#f5d0fe" font-size="18" font-weight="800">每次请求，窗口里装了什么</text>
    <text x="112" y="62" fill="#f4ede4" font-size="15" font-weight="700">全部写进系统提示</text>
    <text x="328" y="62" fill="#f4ede4" font-size="15" font-weight="700">目录 + 按需翻阅</text>
    <g font-size="14">
      <rect x="20" y="76" width="184" height="32" rx="7" fill="rgba(245,208,254,.14)" stroke="#9a93a8"/>
      <text x="112" y="97" fill="#f4ede4">周报格式</text>
      <rect x="20" y="112" width="184" height="32" rx="7" fill="rgba(245,208,254,.14)" stroke="#9a93a8"/>
      <text x="112" y="133" fill="#f4ede4">SQL 规范</text>
      <rect x="20" y="148" width="184" height="32" rx="7" fill="rgba(245,208,254,.14)" stroke="#9a93a8"/>
      <text x="112" y="169" fill="#f4ede4">CSV 清洗规则</text>
      <rect x="20" y="184" width="184" height="32" rx="7" fill="rgba(245,208,254,.14)" stroke="#9a93a8"/>
      <text x="112" y="205" fill="#f4ede4">发版检查清单</text>
      <rect x="20" y="220" width="184" height="32" rx="7" fill="rgba(245,208,254,.14)" stroke="#9a93a8"/>
      <text x="112" y="241" fill="#f4ede4">事故复盘模板</text>
      <rect x="20" y="256" width="184" height="32" rx="7" fill="rgba(245,208,254,.14)" stroke="#9a93a8"/>
      <text x="112" y="277" fill="#f4ede4">……还有二十份</text>
      <rect x="20" y="300" width="184" height="32" rx="7" fill="rgba(255,211,138,.16)" stroke="#ffd38a"/>
      <text x="112" y="321" fill="#ffd38a">用户：审一下这条 SQL</text>
      <rect x="236" y="76" width="184" height="128" rx="7" fill="rgba(255,255,255,.05)" stroke="#9a93a8"/>
      <g text-anchor="start" font-size="13">
        <text x="250" y="100" fill="#9a93a8">· weekly-report：周报</text>
        <text x="250" y="122" fill="#f5d0fe">· sql-review：SQL 审查</text>
        <text x="250" y="144" fill="#9a93a8">· csv-cleanup：CSV</text>
        <text x="250" y="166" fill="#9a93a8">· release-check：发版</text>
        <text x="250" y="188" fill="#9a93a8">· ……每个约一行</text>
      </g>
      <line x1="328" y1="206" x2="328" y2="234" stroke="#f5d0fe" stroke-width="2.5" marker-end="url(#sk-a1)"/>
      <text x="368" y="225" fill="#9a93a8" font-size="13">命中</text>
      <rect x="236" y="238" width="184" height="50" rx="7" fill="rgba(245,208,254,.22)" stroke="#f5d0fe"/>
      <text x="328" y="268" fill="#f4ede4">sql-review 正文</text>
      <rect x="236" y="300" width="184" height="32" rx="7" fill="rgba(255,211,138,.16)" stroke="#ffd38a"/>
      <text x="328" y="321" fill="#ffd38a">用户：审一下这条 SQL</text>
    </g>
    <text x="112" y="366" fill="#9a93a8" font-size="13">每次都为全部内容付费</text>
    <text x="328" y="366" fill="#9a93a8" font-size="13">只为用到的那本付费</text>
  </g>
</svg>
<figcaption>左边每次请求都带着所有说明；右边平时只带一份目录，命中哪个任务才读入哪一份说明</figcaption>
</figure>

把所有说明都写进系统提示，会遇到四类问题：

| 问题 | 表现 | 原因 |
|---|---|---|
| **太长** | 说明越来越多，挤占对话历史和工具结果的空间 | 上下文窗口有上限，系统提示占得越多，留给任务本身的越少 |
| **太贵** | 每次请求都为所有说明付费，延迟也跟着增加 | 模型按输入 token 计费；提示词缓存能打折，但不是免费，而且系统提示一改缓存就失效 |
| **互相干扰** | 写周报时用上了 SQL 审查的格式；两段规则互相矛盾 | 模型会参考上下文里所有内容，无关的说明是噪声，内容越多，关键约束越容易被淹没 |
| **难维护** | 一个大文件，多人修改，没人敢删 | 没有边界、没有负责人、没有版本，也没法单独测试某一段 |

本系列《上下文工程》里讲过，上下文窗口有限且昂贵，**窗口大小是上限，不是目标**。处理工具结果和检索文档时，我们用「按需拉取」的办法（选择、压缩）；那么对「说明书」本身，能不能也按需加载？这就是 Skills 要解决的问题。

## Skill 是什么

### 官方定义

Agent Skills 是 Anthropic 在 2025 年 10 月发布的一种机制，同年 12 月作为**开放标准**发布，规范放在 agentskills.io。它的定义很朴素：

> 一个 Skill 就是一个**文件夹**，里面至少有一个 `SKILL.md` 文件。这个文件包含元数据（至少有 `name` 和 `description`）和告诉 Agent 怎么完成某项任务的指令。文件夹里还可以附带脚本、参考资料、模板等资源。

Anthropic 用了一个类比：写一个 Skill，就像给新员工写一份入职指南。新员工本身很聪明（模型已经有通用能力），缺的是「我们这里的做法」：周报用什么格式、SQL 要遵守什么规范、发版之前检查哪几项。这类知识叫**程序性知识**（procedural knowledge），即「怎么做」，而不是「是什么」。

<figure>
<svg viewBox="0 0 440 380" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="一个 Skill 文件夹的结构">
  <rect width="440" height="380" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif">
    <text x="220" y="30" fill="#f5d0fe" font-size="18" font-weight="800" text-anchor="middle">一个 Skill 文件夹</text>
    <rect x="20" y="50" width="400" height="36" rx="8" fill="rgba(245,208,254,.18)" stroke="#f5d0fe"/>
    <text x="36" y="74" fill="#f4ede4" font-size="15" font-weight="700">csv-cleanup/</text>
    <text x="404" y="74" fill="#9a93a8" font-size="13" text-anchor="end">目录名 = name</text>
    <g stroke="#9a93a8" stroke-width="1.5" fill="none">
      <path d="M40 86 V 302"/>
      <path d="M40 112 H 60"/><path d="M40 238 H 60"/><path d="M40 270 H 60"/><path d="M40 302 H 60"/>
    </g>
    <rect x="62" y="96" width="358" height="128" rx="8" fill="rgba(255,255,255,.05)" stroke="#f5d0fe"/>
    <text x="76" y="118" fill="#f5d0fe" font-size="15" font-weight="800">SKILL.md</text>
    <text x="404" y="118" fill="#9a93a8" font-size="13" text-anchor="end">必需</text>
    <g font-family="Menlo, Consolas, monospace" font-size="13">
      <text x="76" y="142" fill="#9a93a8">---</text>
      <text x="76" y="160" fill="#f4ede4">name: csv-cleanup</text>
      <text x="76" y="178" fill="#f4ede4">description: 做什么 + 何时用</text>
      <text x="76" y="196" fill="#9a93a8">---</text>
      <text x="76" y="213" fill="#ffd38a"># 正文：步骤、检查点、示例</text>
    </g>
    <text x="66" y="243" fill="#f4ede4" font-size="14" font-weight="700">scripts/clean_csv.py</text>
    <text x="404" y="243" fill="#9a93a8" font-size="13" text-anchor="end">可执行脚本</text>
    <text x="66" y="275" fill="#f4ede4" font-size="14" font-weight="700">references/RULES.md</text>
    <text x="404" y="275" fill="#9a93a8" font-size="13" text-anchor="end">参考资料</text>
    <text x="66" y="307" fill="#f4ede4" font-size="14" font-weight="700">assets/</text>
    <text x="404" y="307" fill="#9a93a8" font-size="13" text-anchor="end">模板、数据、图片</text>
    <text x="220" y="350" fill="#9a93a8" font-size="13" text-anchor="middle">只有 SKILL.md 是必需的，其余目录是约定，可选</text>
  </g>
</svg>
<figcaption>Skill 就是一个普通文件夹：SKILL.md 是入口，脚本、参考资料和模板放在旁边，用到时再读</figcaption>
</figure>

### SKILL.md 的格式

`SKILL.md` 由两部分组成：开头用 `---` 包起来的 **YAML 前置元数据**（frontmatter），以及后面的 **Markdown 正文**。

```markdown
---
name: csv-cleanup
description: 清洗和整理 CSV 表格：去掉空行和重复行、统一日期格式……当用户给出 CSV 文件并要求清洗、去重、规范格式时使用。
---

# 整理 CSV

## 步骤
1. ……
```

开放规范对前置元数据的要求：

| 字段 | 是否必需 | 约束 |
|---|---|---|
| `name` | 必需 | 1–64 个字符，只能是小写字母、数字和连字符；不能以连字符开头或结尾，不能有连续的连字符；要和所在目录名一致 |
| `description` | 必需 | 1–1024 个字符；说明这个 Skill 做什么、**什么时候用** |
| `license` | 可选 | 许可证名称，或指向附带的许可证文件 |
| `compatibility` | 可选 | 最多 500 字符，说明环境要求（需要哪些系统工具、是否要联网等） |
| `metadata` | 可选 | 任意的字符串键值对，比如作者、版本号 |
| `allowed-tools` | 可选（实验性） | 预先批准这个 Skill 可以使用的工具，各家实现的支持程度不同 |

Anthropic 自己的平台在此之上还有额外限制，例如 `name` 不能包含 `anthropic`、`claude` 这样的保留词，两个字段里都不能有 XML 标签。各个产品也会加自己的扩展字段（后面会讲到 Claude Code 的几个）。

正文没有格式限制，写什么都行。规范推荐写上：分步骤的操作说明、输入输出示例、常见的边界情况。规范还建议正文控制在 **500 行以内**，更长的内容拆到单独的参考文件里。

### 一个 Skill 的三种内容

| 内容 | 放在哪里 | Agent 怎么用 |
|---|---|---|
| 指令 | `SKILL.md` 正文、`references/*.md` | **读**：读进上下文，按说明去做 |
| 代码 | `scripts/` | **运行**：通过 shell 执行，只有输出进入上下文 |
| 资源 | `assets/` | **按需使用**：模板、数据表、Schema，用到时读取或交给脚本 |

注意「代码」这一行：脚本的源码不需要进入上下文。Agent 只要知道「运行 `python scripts/clean_csv.py 文件名`」，拿到它打印的几行统计就够了。这一点后面的代码实验会量化给你看。

## 渐进式披露：三层加载

<figure>
<svg viewBox="0 0 440 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="渐进式披露的三层">
  <rect width="440" height="360" fill="#0f0e1c"/>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif">
    <text x="220" y="30" fill="#f5d0fe" font-size="18" font-weight="800" text-anchor="middle">渐进式披露：用到才加载</text>
    <rect x="20" y="52" width="400" height="80" rx="10" fill="rgba(245,208,254,.22)" stroke="#f5d0fe"/>
    <text x="36" y="78" fill="#f5d0fe" font-size="16" font-weight="800">第 1 层  元数据</text>
    <text x="36" y="102" fill="#f4ede4" font-size="14">name + description，启动时全部加载</text>
    <text x="36" y="122" fill="#9a93a8" font-size="13">每个 Skill 约 100 token，常驻上下文</text>
    <rect x="20" y="146" width="400" height="80" rx="10" fill="rgba(255,211,138,.12)" stroke="#ffd38a"/>
    <text x="36" y="172" fill="#ffd38a" font-size="16" font-weight="800">第 2 层  SKILL.md 正文</text>
    <text x="36" y="196" fill="#f4ede4" font-size="14">任务命中 description 时读入</text>
    <text x="36" y="216" fill="#9a93a8" font-size="13">建议少于 5000 token</text>
    <rect x="20" y="240" width="400" height="80" rx="10" fill="rgba(134,239,172,.10)" stroke="#86efac"/>
    <text x="36" y="266" fill="#86efac" font-size="16" font-weight="800">第 3 层  附属文件</text>
    <text x="36" y="290" fill="#f4ede4" font-size="14">参考资料按需读，脚本直接运行</text>
    <text x="36" y="310" fill="#9a93a8" font-size="13">不访问就不占上下文；脚本只回传输出</text>
    <text x="220" y="346" fill="#9a93a8" font-size="13" text-anchor="middle">越往下，内容越多，被加载的机会越少</text>
  </g>
</svg>
<figcaption>三层加载：目录常驻，正文命中才读，附属文件用到才读或运行</figcaption>
</figure>

Skills 的核心设计叫**渐进式披露**（progressive disclosure）：信息分层，先给最少的，需要时再给更多。

| 层级 | 什么时候加载 | 大概成本 | 内容 |
|---|---|---|---|
| 第 1 层：元数据 | 启动时，所有 Skill 都加载 | 每个约 100 token | `name` 和 `description` |
| 第 2 层：指令 | 任务和某个 Skill 的描述匹配时 | 官方建议少于 5000 token | `SKILL.md` 正文 |
| 第 3 层：资源 | 正文里提到、任务确实需要时 | 不访问就是 0 | 参考文件被读取时才进上下文；脚本被执行，只有输出进上下文 |

（表中的 token 数字来自 Anthropic 文档和开放规范的建议值，不是硬性限制。）

Anthropic 的比喻是一本组织良好的手册：先看目录，再翻到相关章节，最后才去查附录。因为第 3 层可以无限扩展而不占上下文，**一个 Skill 能附带的知识量实际上没有上限**，比如把整套 API 文档、数据库表结构放进 `references/`，Agent 只在需要时读其中一个文件。

### 一次调用的时序

<figure>
<svg viewBox="0 0 440 470" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="使用 Skill 的一次调用时序">
  <rect width="440" height="470" fill="#0f0e1c"/>
  <defs><marker id="sk-a2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#f5d0fe"/></marker>
  <marker id="sk-a3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9a93a8"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="28" fill="#f5d0fe" font-size="18" font-weight="800">一次「清洗 CSV」请求</text>
    <rect x="20" y="44" width="90" height="34" rx="8" fill="rgba(255,211,138,.16)" stroke="#ffd38a"/>
    <text x="65" y="66" fill="#f4ede4" font-size="14" font-weight="700">用户</text>
    <rect x="170" y="44" width="100" height="34" rx="8" fill="rgba(245,208,254,.2)" stroke="#f5d0fe"/>
    <text x="220" y="66" fill="#f4ede4" font-size="14" font-weight="700">Agent</text>
    <rect x="320" y="44" width="100" height="34" rx="8" fill="rgba(134,239,172,.12)" stroke="#86efac"/>
    <text x="370" y="66" fill="#f4ede4" font-size="14" font-weight="700">文件 / 沙箱</text>
    <g stroke="rgba(255,255,255,.18)" stroke-dasharray="4 5"><line x1="65" y1="78" x2="65" y2="424"/><line x1="220" y1="78" x2="220" y2="424"/><line x1="370" y1="78" x2="370" y2="424"/></g>
    <line x1="364" y1="112" x2="226" y2="112" stroke="#9a93a8" stroke-width="2" marker-end="url(#sk-a3)"/>
    <text x="295" y="104" fill="#9a93a8" font-size="13">① 启动：所有描述</text>
    <line x1="71" y1="160" x2="214" y2="160" stroke="#ffd38a" stroke-width="2" marker-end="url(#sk-a2)"/>
    <text x="142" y="152" fill="#ffd38a" font-size="13">② 清洗这个 CSV</text>
    <rect x="126" y="179" width="188" height="22" rx="6" fill="#0f0e1c" stroke="#f5d0fe" stroke-opacity=".5"/>
    <text x="220" y="194" fill="#f5d0fe" font-size="13">③ 描述匹配 csv-cleanup</text>
    <line x1="226" y1="230" x2="364" y2="230" stroke="#f5d0fe" stroke-width="2" marker-end="url(#sk-a2)"/>
    <text x="295" y="222" fill="#f4ede4" font-size="13">④ 读 SKILL.md</text>
    <line x1="364" y1="256" x2="226" y2="256" stroke="#9a93a8" stroke-width="2" marker-end="url(#sk-a3)"/>
    <text x="295" y="276" fill="#9a93a8" font-size="13">正文进入上下文</text>
    <line x1="226" y1="314" x2="364" y2="314" stroke="#f5d0fe" stroke-width="2" marker-end="url(#sk-a2)"/>
    <text x="295" y="306" fill="#f4ede4" font-size="13">⑤ 运行脚本</text>
    <line x1="364" y1="340" x2="226" y2="340" stroke="#9a93a8" stroke-width="2" marker-end="url(#sk-a3)"/>
    <text x="295" y="360" fill="#9a93a8" font-size="13">只回传 3 行统计</text>
    <line x1="214" y1="410" x2="71" y2="410" stroke="#ffd38a" stroke-width="2" marker-end="url(#sk-a2)"/>
    <text x="142" y="402" fill="#ffd38a" font-size="13">⑥ 汇报结果</text>
    <text x="220" y="442" fill="#9a93a8" font-size="13">references/RULES.md 没被问到，始终没读</text>
  </g>
</svg>
<figcaption>Agent 先靠描述决定用哪个 Skill，再读正文、运行脚本；没用到的参考文件不会进入上下文</figcaption>
</figure>

几个关键点：

1. **选择 Skill 的是模型自己。** 系统把所有 Skill 的名称和描述放进系统提示，模型读到用户请求后，自己判断要不要用、用哪个。所以 `description` 写得好不好，直接决定这个 Skill 会不会被用上。
2. **「读文件」和「运行脚本」靠的是 Agent 已有的工具。** 在 Claude 的实现里，Skill 运行在一个能执行代码的环境中，Agent 用读文件、执行 shell 命令的工具去访问 Skill 文件夹。Skill 本身不是一种新的工具调用协议，它就是**文件系统上的文件**，加上「先读目录」的约定。
3. **正文进入上下文后就留在那里。** 一旦读入，正文就和其他对话内容一样占着窗口，直到被压缩或清理。这也是为什么正文要保持精简。

## 和提示词、工具、MCP、子 Agent 的区别

刚接触 Skills 的人常问：这和写个提示词模板有什么区别？和 MCP 是不是重复了？下面这张表把几个概念放在一起比较：

| | 系统提示 | 工具（Function Calling） | MCP | Skill | 子 Agent |
|---|---|---|---|---|---|
| 解决什么 | 身份、基本规则 | 让模型能调用一个函数 | 用统一协议把外部系统接进来 | 教模型**按什么流程做事** | 把一块工作放到独立窗口里做 |
| 本质 | 一段文本 | 函数的名称、参数 Schema | 客户端-服务器协议，暴露工具、资源、提示 | 文件夹：说明 + 脚本 + 资源 | 另一个模型调用循环 |
| 何时进入上下文 | 每次请求 | 工具定义通常每次都在 | 连接的服务器的工具定义通常都在 | 平时只有描述，用到才读正文 | 只有它的最终结果回到主窗口 |
| 谁来写 | 应用开发者 | 应用开发者 | 服务提供方 | 任何懂这件事的人，会写 Markdown 就行 | 应用开发者 |
| 典型例子 | 「回答要简洁」 | `get_weather(city)` | GitHub、数据库、Jira 的 MCP 服务器 | 「按团队规范审 SQL」 | 「去搜一下相关代码，只回报结论」 |

<figure>
<svg viewBox="0 0 440 360" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="MCP 提供能力，Skill 提供方法">
  <rect width="440" height="360" fill="#0f0e1c"/>
  <defs><marker id="sk-a4" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#f5d0fe"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="30" fill="#f5d0fe" font-size="18" font-weight="800">MCP 给「手」，Skill 给「手册」</text>
    <rect x="20" y="52" width="190" height="140" rx="10" fill="rgba(245,208,254,.16)" stroke="#f5d0fe"/>
    <text x="115" y="78" fill="#f5d0fe" font-size="16" font-weight="800">Skill：事故复盘</text>
    <g font-size="13" fill="#f4ede4" text-anchor="start">
      <text x="34" y="104">1. 查告警时间线</text>
      <text x="34" y="126">2. 拉相关工单</text>
      <text x="34" y="148">3. 按模板写复盘</text>
      <text x="34" y="170">4. 检查行动项负责人</text>
    </g>
    <rect x="230" y="52" width="190" height="140" rx="10" fill="rgba(134,239,172,.10)" stroke="#86efac"/>
    <text x="325" y="78" fill="#86efac" font-size="16" font-weight="800">MCP 服务器</text>
    <g font-size="13" fill="#f4ede4" text-anchor="start">
      <text x="244" y="104">监控：query_alerts</text>
      <text x="244" y="126">工单：search_issues</text>
      <text x="244" y="148">文档：create_page</text>
    </g>
    <text x="325" y="176" fill="#9a93a8" font-size="13">能连上、能调用</text>
    <line x1="115" y1="194" x2="200" y2="240" stroke="#f5d0fe" stroke-width="2.5" marker-end="url(#sk-a4)"/>
    <line x1="325" y1="194" x2="240" y2="240" stroke="#86efac" stroke-width="2.5" marker-end="url(#sk-a4)"/>
    <rect x="110" y="242" width="220" height="56" rx="12" fill="rgba(255,211,138,.14)" stroke="#ffd38a"/>
    <text x="220" y="266" fill="#ffd38a" font-size="16" font-weight="800">Agent</text>
    <text x="220" y="287" fill="#f4ede4" font-size="13">知道做什么，也做得到</text>
    <text x="220" y="330" fill="#9a93a8" font-size="13">只有工具：会调用，但不知道你们的流程</text>
    <text x="220" y="350" fill="#9a93a8" font-size="13">只有 Skill：知道流程，但够不着数据</text>
  </g>
</svg>
<figcaption>MCP 负责连接外部系统、提供可调用的工具；Skill 负责告诉 Agent 按什么顺序、用哪些工具、怎么检查结果</figcaption>
</figure>

### Skill 与 MCP：能力和方法

这是最容易混淆的一组。一句话区分：**MCP 提供能力和连接，Skill 提供做事的方法和流程。**

- MCP 服务器让 Agent「够得着」：能查监控、能搜工单、能写文档（见本系列《Function Calling 与 MCP》）；
- 但够得着不等于会做。「事故复盘」在你们团队有固定流程：先拉告警时间线，再查相关工单，按模板写，每个行动项必须有负责人和截止日期。这些是 Skill 的内容。

两者是配合关系。一个 Skill 可以在正文里写「用监控 MCP 的 `query_alerts` 查最近 24 小时的告警」，Anthropic 的最佳实践还建议在 Skill 里使用带服务器前缀的完整工具名，避免多个 MCP 服务器有同名工具时用错。OpenAI Codex 的 Skill 甚至可以在附带的配置文件里声明它依赖哪个 MCP 服务器。

成本上也有区别：MCP 服务器的工具定义一般在连接后就全部放进上下文（工具多了同样会撑大窗口，有些产品为此做了按需搜索工具的功能）；Skill 天生就是按需加载。所以有一种经验做法：**能用一段说明加一个脚本解决的事，不一定要做成 MCP 服务器**；需要访问外部系统、需要鉴权、需要被很多不同的 Agent 复用的能力，才值得做成 MCP。

### Skill 与提示词

Skill 的正文本质上就是提示词。区别在于**组织方式**：

- 普通提示词是一次性的，写在某次对话或某个系统提示里；
- Skill 是有名字、有描述、有版本的文件夹，可以被发现、按需加载、在多个项目和产品之间复用，还能带上脚本和资源。

本系列《Prompt 工程与结构化输出》里讲的写法（说清楚目标、给示例、定义输出格式），在写 Skill 正文时全部适用。

### Skill 与工具

工具是一个**动作**（调用一个函数），Skill 是一套**做法**（可能包含很多个动作，以及什么时候做、做完怎么检查）。Skill 里的脚本也是通过 Agent 已有的「执行命令」工具去运行的，Skill 并没有引入新的工具。

### Skill 与子 Agent

子 Agent 解决的是**上下文隔离**：把一块会产生大量中间结果的工作放到独立窗口里做，只把结论带回来（见本系列《多 Agent 协作》）。Skill 解决的是**知识的按需加载**。两者可以组合：Claude Code 允许在 Skill 的前置元数据里写 `context: fork`，让这个 Skill 在一个子 Agent 里运行，正文就成为子 Agent 的任务说明。

## 动手：一个迷你 Skill 加载器

下面用 Python 标准库实现一个最小的 Skill 系统，把渐进式披露的每一步都打印出来，并和「全部写进系统提示」比较 token 数。

这里用一个**假模型**代替真实 LLM：`fake_llm_choose` 根据用户请求和描述的字面重合度选择 Skill，`fake_llm_follow` 从正文里找出要运行的命令。它们是确定性的规则，目的是把流程完整跑通。**换成真实 API，只需要替换这两个函数**：把技能目录和用户请求发给模型，让模型返回要用的 Skill 名称；再把正文发给模型，让它通过执行命令的工具去运行脚本。

### 目录结构

```text
agent-skills-code/
├── skill_loader.py
├── data/
│   ├── worklog.txt
│   └── sales.csv
└── skills/
    ├── weekly-report/
    │   ├── SKILL.md
    │   ├── scripts/make_report.py
    │   └── assets/template.md
    ├── csv-cleanup/
    │   ├── SKILL.md
    │   ├── scripts/clean_csv.py
    │   └── references/RULES.md
    └── sql-review/
        ├── SKILL.md
        └── references/LOCKS.md
```

### 一个完整的 SKILL.md

这是「生成周报」这个 Skill 的完整内容，可以当作写 Skill 的模板来看：描述里写清做什么和何时用；正文有适用范围、步骤、检查点、写法要求、示例和反例；确定性的统计交给脚本；模板放在 `assets/` 里，只在需要时读取。

````markdown
---
name: weekly-report
description: 根据 git 提交记录或工作流水生成团队周报，按「本周完成 / 进行中 / 风险 / 下周计划」四段输出。当用户要求写周报、汇总本周工作、整理提交记录时使用。
license: MIT
metadata:
  owner: platform-team
  version: "1.2"
---

# 生成周报

## 什么时候用
用户要写周报、周总结，或者给出一段提交记录 / 工作流水，希望整理成可以发给团队的文字。
如果用户要的是月报或述职材料，不要用这个 Skill。

## 步骤
1. 确认输入：一个文本文件，每行一条记录，格式为 `日期 | 作者 | 类型 | 说明`。
   类型只能是 feat / fix / wip / risk 四种之一。
2. 运行脚本做确定性的分组和计数，不要自己数：
   ```bash
   python scripts/make_report.py <输入文件>
   ```
3. 脚本输出的是草稿。你只需要补充「下周计划」，其余段落不要改写数字。
4. 检查点（全部满足才能交付）：
   - [ ] 四个小节都在，顺序是 本周完成 → 进行中 → 风险 → 下周计划
   - [ ] 「本周完成」的条数与脚本统计一致
   - [ ] 每条风险都写了负责人

## 写法要求
- 每条一句话，动词开头，不写「努力」「积极」之类的形容词。
- 同一件事的多次提交合并成一条。
- 数字一律用阿拉伯数字。

## 示例
输入：
```
2026-10-12 | 小王 | feat | 订单列表支持按状态筛选
2026-10-13 | 小李 | risk | 支付回调偶发超时，排查中
```
输出片段：
```
本周完成（1）
- 订单列表支持按状态筛选（小王）
风险（1）
- 支付回调偶发超时，排查中（负责人：小李）
```

## 反例
- 不要把 wip 写进「本周完成」。
- 不要编造输入里没有的工作。

## 模板
最终格式见 assets/template.md，只在需要核对格式时读取。
````

它附带的脚本 `scripts/make_report.py`：

```python
"""把工作流水按类型分组，输出周报草稿。确定性的统计交给代码，不交给模型。"""
import sys
from collections import defaultdict

SECTIONS = [("feat", "本周完成"), ("fix", "本周完成"), ("wip", "进行中"), ("risk", "风险")]


def main(path):
    groups = defaultdict(list)
    bad = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 4 or parts[2] not in {"feat", "fix", "wip", "risk"}:
                bad += 1
                continue
            _, author, kind, text = parts
            title = dict(SECTIONS)[kind]
            item = f"- {text}（负责人：{author}）" if kind == "risk" else f"- {text}（{author}）"
            if item not in groups[title]:          # 同一件事只写一次
                groups[title].append(item)
    for title in ["本周完成", "进行中", "风险"]:
        print(f"{title}（{len(groups[title])}）")
        print("\n".join(groups[title]) or "- 无")
    print("下周计划\n- （待补充）")
    if bad:
        print(f"[警告] 跳过 {bad} 行格式不对的记录", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1])
```

另外两个 Skill 结构相同。`csv-cleanup` 的描述是「清洗和整理 CSV 表格：去掉空行和重复行、统一日期格式、金额转成数字、标出无法解析的单元格。当用户给出 CSV 文件并要求清洗、去重、规范格式或做导入前检查时使用」，正文要求「先只读前 5 行看表头」「所有改动都通过脚本完成」「不要删除无法解析的行，只标记」。它的脚本 `scripts/clean_csv.py`：

```python
"""CSV 清洗：去空行、去重、统一日期、金额转数字。只打印统计，不打印数据本身。"""
import csv
import re
import sys

DATE_PATTERNS = [
    (re.compile(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$"), (1, 2, 3)),   # 2026/10/3
    (re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$"), (3, 1, 2)),           # 10/3/2026（月/日/年）
]


def norm_date(s):
    for pat, (y, m, d) in DATE_PATTERNS:
        g = pat.match(s.strip())
        if g:
            return f"{int(g.group(y)):04d}-{int(g.group(m)):02d}-{int(g.group(d)):02d}"
    return None


def norm_amount(s):
    s = s.strip().replace(",", "").replace("¥", "").replace("元", "")
    try:
        return f"{float(s):.2f}"
    except ValueError:
        return None


def main(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], rows[1:]
    out, seen, stats = [header + ["问题"]], set(), {"空行": 0, "重复": 0, "无法解析": []}
    for lineno, row in enumerate(body, start=2):
        if not any(c.strip() for c in row):
            stats["空行"] += 1
            continue
        rec = dict(zip(header, row))
        date, amount = norm_date(rec["日期"]), norm_amount(rec["金额"])
        problem = []
        if date is None:
            problem.append("日期")
        if amount is None:
            problem.append("金额")
        key = (date or rec["日期"], rec["客户"].strip(), amount or rec["金额"])
        if key in seen:
            stats["重复"] += 1
            continue
        seen.add(key)
        if problem:
            stats["无法解析"].append(f"第{lineno}行({'/'.join(problem)})")
        out.append([date or rec["日期"], rec["客户"].strip(), amount or rec["金额"], ",".join(problem)])
    dst = path.rsplit(".", 1)[0] + ".clean.csv"
    with open(dst, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(out)
    print(f"原始 {len(body)} 行 → 输出 {len(out) - 1} 行；空行 {stats['空行']}，重复 {stats['重复']}")
    print("无法解析：" + ("、".join(stats["无法解析"]) or "无"))
    print(f"已写入 {dst.split('/')[-1]}")


if __name__ == "__main__":
    main(sys.argv[1])
```

`sql-review` 没有脚本，正文是一份按「查询 / 写入 / DDL」分类的审查清单，另有一份锁相关的参考文件。

测试数据 `data/worklog.txt`（故意放了一条重复记录和一条格式错误的记录）：

```text
2026-10-12 | 小王 | feat | 订单列表支持按状态筛选
2026-10-12 | 小王 | feat | 订单列表支持按状态筛选
2026-10-13 | 小李 | fix | 修复导出 Excel 时中文文件名乱码
2026-10-13 | 小李 | risk | 支付回调偶发超时，排查中
2026-10-14 | 小张 | wip | 优惠券服务拆分，完成 60%
2026-10-15 | 小张 | 本周开会三次
```

`data/sales.csv`（日期格式混乱、有重复、有空行、有无效值）：

```text
日期,客户,金额
2026/10/3,星辰科技,"1,200"
2026-10-03, 星辰科技 ,1200.00
10/5/2026,云帆物流,¥860

2026.10.8,北斗餐饮,350元
上周三,蓝鲸教育,500
2026-10-09,星辰科技,abc
```

### 加载器

```python
"""迷你 Skill 加载器：渐进式披露的三层加载 + 与「全部塞进系统提示」的对比。

这里用一个假模型（fake_llm_choose / fake_llm_follow）代替真实 LLM，
换成真实 API 只需替换这两个函数。
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SKILLS_DIR = ROOT / "skills"
BASE_SYSTEM = "你是团队里的工程助手。回答简洁，先给结论。需要时可以使用下面列出的技能。"


# ---------- 工具函数 ----------
def est_tokens(text):
    """粗估 token：汉字和中文标点约 1 个 token，其余字符约 4 个一个 token。"""
    cjk = len(re.findall(r"[一-鿿　-〿＀-￯]", text))
    other = len(re.sub(r"[一-鿿　-〿＀-￯\s]", "", text))
    return cjk + (other + 3) // 4


def parse_frontmatter(text):
    """手写的极简 YAML 前置元数据解析：支持 key: value 和一层缩进的 map。"""
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md 必须以 --- 开头")
    head, body = text[4:].split("\n---\n", 1)
    meta, current = {}, None
    for line in head.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, value = line.strip().partition(":")
        value = value.strip().strip('"').strip("'")
        if line.startswith("  ") and current is not None:   # 子字段，例如 metadata.version
            meta[current][key] = value
        elif value == "":                                    # 下面跟着一个 map
            current = key
            meta[key] = {}
        else:
            current = None
            meta[key] = value
    return meta, body.lstrip("\n")


NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate(meta, dirname):
    name, desc = meta.get("name", ""), meta.get("description", "")
    errors = []
    if not (1 <= len(name) <= 64 and NAME_RE.match(name)):
        errors.append("name 只能是小写字母、数字和单个连字符，1–64 字符")
    if name != dirname:
        errors.append(f"name 应与目录名一致（{dirname}）")
    if not (1 <= len(desc) <= 1024):
        errors.append("description 必须是 1–1024 字符")
    return errors


# ---------- 第 1 层：启动时只读元数据 ----------
def discover():
    skills = {}
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        errs = validate(meta, path.parent.name)
        if errs:
            print(f"  跳过 {path.parent.name}：{'；'.join(errs)}")
            continue
        skills[meta["name"]] = {"dir": path.parent, "description": meta["description"],
                                "version": meta.get("metadata", {}).get("version", "-")}
    return skills


def catalog_text(skills):
    lines = ["<available_skills>"]
    for name, s in skills.items():
        lines.append(f"- {name}: {s['description']}")
    lines.append("</available_skills>")
    return "\n".join(lines)


# ---------- 假模型 ----------
def grams(text):
    """汉字取相邻两字，英文取整个单词（小写）。"""
    text = text.lower()
    words = set(re.findall(r"[a-z]{2,}", text))
    for run in re.findall(r"[一-鿿]+", text):
        words |= {run[i:i + 2] for i in range(len(run) - 1)}
    return words


def fake_llm_choose(catalog, request):
    """假模型第 1 步：读目录，决定用哪个 Skill（或不用）。真实系统里这是一次 LLM 调用。"""
    best, best_score = None, 0
    for line in catalog.splitlines():
        m = re.match(r"- ([a-z0-9-]+): (.*)", line)
        if m:
            score = len(grams(request) & grams(m.group(2)))
            if score > best_score:
                best, best_score = m.group(1), score
    return (best, best_score) if best_score >= 3 else (None, best_score)


def fake_llm_follow(body):
    """假模型第 2 步：读正文，找出要运行的命令。真实模型会理解整段说明，这里只取第一个 bash 代码块。"""
    m = re.search(r"```bash\n(.*?)\n\s*```", body, re.S)
    return m.group(1).strip() if m else None


# ---------- 一次请求的完整流程 ----------
def handle(request, input_file, skills):
    print(f"\n用户：{request}")
    catalog = catalog_text(skills)
    ctx = [BASE_SYSTEM, catalog, request]
    print(f"  [1] 系统提示 + 技能目录 + 请求  ≈ {est_tokens(chr(10).join(ctx))} tokens")

    name, score = fake_llm_choose(catalog, request)
    if name is None:
        print(f"  [2] 没有匹配的技能（最高重合 {score}），直接回答")
        return
    skill = skills[name]
    _, body = parse_frontmatter((skill["dir"] / "SKILL.md").read_text(encoding="utf-8"))
    ctx.append(body)
    print(f"  [2] 选中 {name} v{skill['version']}（重合 {score}），读入正文 +{est_tokens(body)}"
          f" → ≈ {est_tokens(chr(10).join(ctx))} tokens")

    cmd = fake_llm_follow(body)
    if cmd:
        cmd = cmd.replace("<输入文件>", str(input_file)).replace("<input>", str(input_file))
        script = skill["dir"] / cmd.split()[1]
        result = subprocess.run([sys.executable, str(script), str(input_file)],
                                capture_output=True, text=True, cwd=skill["dir"], timeout=30)
        output = (result.stdout + result.stderr).strip()
        ctx.append(output)
        print(f"  [3] 运行 {cmd.split()[1]}（脚本源码 {est_tokens(script.read_text(encoding='utf-8'))}"
              f" tokens，不进上下文），输出 +{est_tokens(output)} → ≈ {est_tokens(chr(10).join(ctx))} tokens")
        for line in output.splitlines():
            print("      │ " + line)


def everything_in_system_prompt(skills):
    """对照组：把所有 Skill 的说明和参考文件都写进系统提示。"""
    parts = [BASE_SYSTEM]
    for s in skills.values():
        for f in sorted(s["dir"].rglob("*.md")):
            parts.append(f.read_text(encoding="utf-8"))
    return est_tokens("\n".join(parts))


if __name__ == "__main__":
    print("== 启动：扫描 skills/ 目录")
    skills = discover()
    for name, s in skills.items():
        full = est_tokens((s["dir"] / "SKILL.md").read_text(encoding="utf-8"))
        print(f"  {name:14s} 描述 {est_tokens(s['description']):3d} tokens  | 完整 SKILL.md {full} tokens")

    print("\n== 渐进式披露")
    handle("帮我把这周的工作流水整理成周报", ROOT / "data/worklog.txt", skills)
    handle("这个 CSV 有重复行，日期格式也乱，帮我清洗一下", ROOT / "data/sales.csv", skills)
    handle("北京明天会下雨吗", None, skills)

    print("\n== 对照：全部塞进系统提示")
    meta_cost = est_tokens(catalog_text(skills))
    all_cost = everything_in_system_prompt(skills)
    print(f"  每次请求的固定开销：目录方式 ≈ {est_tokens(BASE_SYSTEM) + meta_cost} tokens，"
          f"全量方式 ≈ {all_cost} tokens")
    n = len(skills)
    for k in (10, 50, 200):
        print(f"  假设有 {k:3d} 个同样大小的技能：目录 ≈ {meta_cost * k // n:6d} tokens，"
              f"全量 ≈ {(all_cost - est_tokens(BASE_SYSTEM)) * k // n:6d} tokens")
```

运行 `python3 skill_loader.py`，输出（Python 3.13）：

```text
== 启动：扫描 skills/ 目录
  csv-cleanup    描述  75 tokens  | 完整 SKILL.md 398 tokens
  sql-review     描述  67 tokens  | 完整 SKILL.md 505 tokens
  weekly-report  描述  67 tokens  | 完整 SKILL.md 555 tokens

== 渐进式披露

用户：帮我把这周的工作流水整理成周报
  [1] 系统提示 + 技能目录 + 请求  ≈ 278 tokens
  [2] 选中 weekly-report v1.2（重合 5），读入正文 +467 → ≈ 744 tokens
  [3] 运行 scripts/make_report.py（脚本源码 259 tokens，不进上下文），输出 +106 → ≈ 850 tokens
      │ 本周完成（2）
      │ - 订单列表支持按状态筛选（小王）
      │ - 修复导出 Excel 时中文文件名乱码（小李）
      │ 进行中（1）
      │ - 优惠券服务拆分，完成 60%（小张）
      │ 风险（1）
      │ - 支付回调偶发超时，排查中（负责人：小李）
      │ 下周计划
      │ - （待补充）
      │ [警告] 跳过 1 行格式不对的记录

用户：这个 CSV 有重复行，日期格式也乱，帮我清洗一下
  [1] 系统提示 + 技能目录 + 请求  ≈ 284 tokens
  [2] 选中 csv-cleanup v0.9（重合 7），读入正文 +303 → ≈ 586 tokens
  [3] 运行 scripts/clean_csv.py（脚本源码 458 tokens，不进上下文），输出 +36 → ≈ 622 tokens
      │ 原始 7 行 → 输出 5 行；空行 1，重复 1
      │ 无法解析：第7行(日期)、第8行(金额)
      │ 已写入 sales.clean.csv

用户：北京明天会下雨吗
  [1] 系统提示 + 技能目录 + 请求  ≈ 271 tokens
  [2] 没有匹配的技能（最高重合 0），直接回答

== 对照：全部塞进系统提示
  每次请求的固定开销：目录方式 ≈ 263 tokens，全量方式 ≈ 1811 tokens
  假设有  10 个同样大小的技能：目录 ≈    756 tokens，全量 ≈   5916 tokens
  假设有  50 个同样大小的技能：目录 ≈   3783 tokens，全量 ≈  29583 tokens
  假设有 200 个同样大小的技能：目录 ≈  15133 tokens，全量 ≈ 118333 tokens
```

> 这里的 token 数是按「一个汉字约 1 个 token、其他字符约 4 个一个 token」粗估的，不同模型的分词器结果会有出入，看相对大小即可。

### 读懂这段输出

**第 1 层很便宜。** 三个 Skill 的描述加起来两百多 token，「北京明天会下雨吗」这种和任何 Skill 都无关的请求，只付这点固定成本。

**第 2 层只读一份。** 写周报时只读入 `weekly-report` 的正文，`sql-review` 的五百多 token 完全没有出现。这正是开头那个团队缺的东西：写周报时，SQL 规范根本不在窗口里，也就不可能被误用。

**第 3 层：脚本不进上下文。** `clean_csv.py` 的源码约 458 token，但进入上下文的只有它打印的 3 行统计（约 36 token）。如果让模型自己去读整份 CSV、逐行判断日期格式，表格有一万行时，消耗的 token 和出错的机会都会大很多。脚本是确定性的：同样的输入，每次结果一样，可以重复执行、可以写单元测试。

**参考文件没被读。** `references/RULES.md` 和 `assets/template.md` 在这两次请求里都没有被访问，成本为 0。只有用户追问「为什么 `上周三` 被判为无效」时，才需要去读 `RULES.md`。

**规模越大，差距越大。** 3 个 Skill 时差距是 263 对 1811；外推到 200 个同样大小的 Skill，全量方式每次请求要十几万 token，已经超过很多模型的窗口，而目录方式约一万五千 token。目录本身也会随数量线性增长，所以各家产品都给技能目录设了预算（后面会讲到）。

### 名称校验

加载器在启动时会校验前置元数据，不合规的 Skill 直接跳过。单独测试一下 `validate`：

```python
from skill_loader import validate

cases = [
    ({"name": "weekly-report", "description": "生成周报……"}, "weekly-report"),
    ({"name": "Weekly_Report", "description": "生成周报……"}, "Weekly_Report"),
    ({"name": "csv--cleanup", "description": "x"}, "csv--cleanup"),
    ({"name": "sql-review", "description": ""}, "sql-review"),
    ({"name": "helper", "description": "帮忙处理各种事情"}, "my-helper"),
]
for meta, d in cases:
    errs = validate(meta, d)
    print(f"{meta['name']:15s} {'通过' if not errs else '；'.join(errs)}")
```

输出：

```text
weekly-report   通过
Weekly_Report   name 只能是小写字母、数字和单个连字符，1–64 字符
csv--cleanup    name 只能是小写字母、数字和单个连字符，1–64 字符
sql-review      description 必须是 1–1024 字符
helper          name 应与目录名一致（my-helper）
```

开放规范提供了一个参考校验工具 `skills-ref`（`skills-ref validate ./my-skill`），检查的就是这些规则。最后一行的 `helper` 虽然被拒绝的原因是目录名不一致，但这个名字本身也不好，后面会讲到。

### 在真实产品里怎么用

在 Claude Code 里，把 Skill 文件夹放到项目的 `.claude/skills/` 或个人的 `~/.claude/skills/` 下就会被自动发现，不需要写加载器。在 Claude API 里，Skill 运行在代码执行工具的容器中。下面是**参考写法**（需要 API Key，本文没有实际运行；模型名请换成支持代码执行工具的模型）：

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="<支持代码执行的模型>",
    max_tokens=4096,
    container={
        "skills": [
            {"type": "anthropic", "skill_id": "xlsx", "version": "latest"},   # 官方预置 Skill
            {"type": "custom", "skill_id": "<上传后得到的 skill_id>", "version": "latest"},
        ]
    },
    tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
    messages=[{"role": "user", "content": "把 sales.csv 清洗一下，再做成带图表的 Excel"}],
)
```

按官方文档：自定义 Skill 通过 `/v1/skills` 接口上传；一次请求最多带 20 个 Skill；单个 Skill 上传上限 30 MB；API 的执行环境**没有网络访问**，也不能在运行时安装软件包。官方预置了 `pptx`、`xlsx`、`docx`、`pdf` 四个处理文档的 Skill。生产环境建议把 `version` 固定成具体版本，而不是 `latest`。

## 写好一个 Skill

Skill 的格式很简单，难的是写好。下面的经验大多来自 Anthropic 的 Skill 编写最佳实践文档和开放规范。

### description 决定会不会被用上

模型只能看到描述，看不到正文。描述没写到的场景，Skill 就不会被触发；描述写得太宽泛，又会在不该用的时候被触发。

| 写法 | 例子 | 问题 |
|---|---|---|
| 太空泛 | 「帮助处理文档。」 | 不知道是什么文档、做什么处理 |
| 只说做什么 | 「从 PDF 提取文字和表格。」 | 没说什么时候用，模型不容易和用户的说法对上 |
| 用第一人称 | 「我可以帮你处理 Excel。」 | 描述会被放进系统提示，第一人称容易造成视角混乱，官方建议用第三人称 |
| **推荐** | 「从 PDF 提取文字和表格、填写表单、合并文件。当用户处理 PDF，或提到表单、文档提取时使用。」 | 做什么 + 何时用 + 用户可能说的关键词 |

几条具体建议：

- **把最关键的用途写在最前面。** 技能多了以后，产品会截断过长的描述。Claude Code 的文档写明，技能列表里每个 Skill 的描述（连同 `when_to_use` 字段）超过 1536 个字符会被截断；OpenAI Codex 则把初始技能列表限制在上下文窗口的约 2%；
- **写进用户真实会说的词。** 用户说「周总结」「这周干了啥」，描述里最好也有；
- **写明边界。** 「月报和述职材料不要用」这类排除条件可以写在正文，也可以在描述里简要提一句；
- **名字要具体。** 官方建议用动名词形式（如 `processing-pdfs`），避免 `helper`、`utils`、`tools` 这种什么都能装的名字。

### 正文：写流程和检查点，不写常识

模型已经很聪明，正文只需要写**它不知道的东西**：你们团队的格式、顺序、约束、坑。不需要解释 PDF 是什么、CSV 是什么。

一个好的正文通常包括：

1. **适用范围**：什么时候用，什么时候不要用；
2. **步骤**：按顺序列出，复杂任务给出可以逐项勾选的清单；
3. **检查点**：交付前必须满足的条件。官方推荐「执行 → 校验 → 修复 → 再校验」的循环，比如「改完运行 `validate.py`，失败就修，通过了才继续」；
4. **示例**：一组输入输出，比任何形容词都清楚；
5. **反例**：常见的错误做法，明确写「不要」；
6. **附属文件的指引**：什么情况下读哪个文件、运行哪个脚本。

### 自由度要和任务的脆弱程度匹配

官方文档有一个很实用的原则：给模型多大的自由，取决于这件事出错的代价。

| 自由度 | 写法 | 适合 |
|---|---|---|
| 高 | 文字描述目标和原则 | 有多种合理做法的任务，比如代码审查、写文案 |
| 中 | 伪代码，或带参数的脚本 | 有推荐做法、但允许调整的任务 |
| 低 | 「严格运行这个脚本，不要改命令、不要加参数」 | 脆弱的操作，比如数据库迁移、批量删除 |

对于批量或破坏性的操作，可以用「计划 → 校验 → 执行」的模式：先让模型生成一份变更清单（比如 `changes.json`），用脚本校验清单，校验通过后再执行。

### 把确定性的步骤交给脚本

Anthropic 在介绍 Skills 的文章里举过一个例子：给一个列表排序，用模型逐个生成 token 来排，比运行一个排序算法贵得多，也更容易出错。凡是**规则明确、需要精确、需要重复执行**的步骤，都应该写成脚本：

- 统计、去重、格式转换、校验；
- 从大文件里提取需要的部分（只打印结果，不打印全文）；
- 调用固定的命令序列。

写脚本也有讲究：

- **自己处理错误**，打印清楚的错误信息，不要把异常栈甩给模型去猜；
- **常量要有理由**，比如超时时间为什么是 30 秒，写在注释里；
- **说清楚是运行还是阅读**：「运行 `scripts/x.py`」和「参考 `scripts/x.py` 的写法」是两回事；
- **不要假设依赖已经装好**，在正文里写出安装命令，或者在 `compatibility` 字段里说明。

### 保持简洁，拆分文件

- `SKILL.md` 正文控制在 500 行以内，详细资料拆到 `references/`；
- 引用只保留**一层深**：SKILL.md 指向参考文件，参考文件不要再层层指向别的文件。官方提到，嵌套太深时模型可能只读一部分（比如只看前 100 行）；
- 超过 100 行的参考文件，开头放一个目录；
- 按领域拆分：一个查询数据仓库的 Skill，可以把财务、销售、产品的表结构分别放在三个文件里，模型只读当前问题相关的那个；
- 文件名要能看出内容，比如 `form_validation_rules.md`，不要叫 `doc2.md`；
- 不要写会过期的内容（「2025 年 8 月之前用旧接口」），把旧做法放进单独的「旧版说明」小节。

### 先有评测，再写 Skill

这一点最容易被忽视。官方建议的顺序是：

1. 先**不用 Skill**，让 Agent 跑几个有代表性的任务，记录它在哪里出错；
2. 针对这些问题写至少三个评测用例；
3. 写**最少量**的说明，让评测通过；
4. 持续观察 Agent 实际怎么使用这个 Skill：是不是读了不该读的文件、漏读了该读的文件、某个附属文件从来没被访问过。

一个具体做法是用两个会话：在一个会话里和模型一起起草、修改 Skill；在另一个全新的会话里加载这个 Skill 去做真实任务，把观察到的问题带回第一个会话修改。本系列《评估（Evals）》里讲的方法同样适用于 Skill。

还有一点：如果要在不同大小的模型上使用，要分别测试。小模型可能需要更多细节，大模型面对过多解释反而可能被干扰。

## 组织、版本与团队共享

### Skill 放在哪里

不同产品会扫描不同的位置，但思路一致：**个人级**的 Skill 放在用户目录，**项目级**的 Skill 放在仓库里跟着代码走。

| 产品 | 项目级 | 个人级 | 其他 |
|---|---|---|---|
| Claude Code | `.claude/skills/<name>/` | `~/.claude/skills/<name>/` | 企业托管目录；插件里的 Skill 以 `插件名:技能名` 命名 |
| OpenAI Codex | 从当前目录到仓库根的每一级 `.agents/skills/` | `~/.agents/skills/` | 管理员目录、内置 Skill |
| GitHub Copilot | `.github/skills/`、`.claude/skills/` 或 `.agents/skills/` | `~/.copilot/skills/` 或 `~/.agents/skills/` | — |

（以上路径来自各产品 2026 年的官方文档，产品更新较快，以最新文档为准。）

可以看到，`.agents/skills/` 正在成为一个跨产品的通用位置。因为格式是开放标准，同一个 Skill 文件夹通常可以在多个产品里直接使用，只有各家的扩展字段（比如 Claude Code 的 `context: fork`、Codex 的 `agents/openai.yaml`）是各自识别的。

### 同名冲突与优先级

多个位置有同名 Skill 时，各家规则不同。Claude Code 的规则是企业级覆盖个人级，个人级覆盖项目级；插件里的 Skill 带命名空间，不会冲突。Codex 则不合并同名 Skill，两个都会出现在选择列表里。团队里最好约定命名前缀，避免撞名。

### 谁来触发

默认情况下，Skill 既可以被模型自动选中，也可以由用户手动调用。有些 Skill 不适合让模型自己决定什么时候用，比如「发布到生产环境」。Claude Code 提供了几个开关：

- `disable-model-invocation: true`：只能由用户输入 `/技能名` 手动触发；
- `user-invocable: false`：只能由模型调用，不出现在用户的命令菜单里；
- `allowed-tools`：调用这个 Skill 时预先批准某些工具，比如只允许 `git add` 和 `git commit`。

Claude Code 原来的「自定义斜杠命令」也已经并入了 Skills：`.claude/commands/deploy.md` 和 `.claude/skills/deploy/SKILL.md` 都会生成 `/deploy` 命令。Codex 也有类似的开关，可以在 `agents/openai.yaml` 里关闭隐式调用，只允许用户显式调用。

### 版本管理

Skill 是普通文件，用 Git 管理即可：

- **项目级 Skill 跟代码一起提交**，代码改了，相关的 Skill 在同一个 PR 里更新，评审时一起看；
- 在 `metadata` 里写上 `version` 和 `owner`，出问题知道找谁；
- 改动 Skill 后跑一遍评测用例，和改代码后跑单元测试一样；
- 通过 API 使用时，生产环境固定版本号，新版本先在测试环境验证。

### 团队共享

- **放在仓库里**：最简单，克隆仓库就有，适合和某个项目强相关的 Skill；
- **做成插件**：Claude Code 可以通过插件分发一组 Skill，适合跨项目通用的 Skill；
- **组织级上传**：通过 Claude API 上传的自定义 Skill 在整个工作区共享。注意各个平台之间**不会自动同步**，在 claude.ai 上传的 Skill 不会出现在 API 里，反之亦然；
- **公共仓库**：Anthropic 在 GitHub 的 `anthropics/skills` 仓库里开源了一批示例 Skill，社区也有很多 Skill 集合。用之前请看下一节。

## 安全：Skill 就是会被执行的代码

<figure>
<svg viewBox="0 0 440 380" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="安装 Skill 时的信任边界">
  <rect width="440" height="380" fill="#0f0e1c"/>
  <defs><marker id="sk-a5" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#f5d0fe"/></marker></defs>
  <g font-family="PingFang SC, Noto Sans SC, sans-serif" text-anchor="middle">
    <text x="220" y="30" fill="#f5d0fe" font-size="18" font-weight="800">装一个 Skill，等于装一个软件</text>
    <rect x="20" y="50" width="190" height="72" rx="10" fill="rgba(134,239,172,.10)" stroke="#86efac"/>
    <text x="115" y="78" fill="#86efac" font-size="15" font-weight="800">可信来源</text>
    <text x="115" y="102" fill="#f4ede4" font-size="13">自己写的、官方的</text>
    <rect x="230" y="50" width="190" height="72" rx="10" fill="rgba(255,138,138,.10)" stroke="#ff8a8a"/>
    <text x="325" y="78" fill="#ff8a8a" font-size="15" font-weight="800">来源不明</text>
    <text x="325" y="102" fill="#f4ede4" font-size="13">网上下载、市场安装</text>
    <line x1="325" y1="124" x2="325" y2="150" stroke="#f5d0fe" stroke-width="2.5" marker-end="url(#sk-a5)"/>
    <rect x="230" y="152" width="190" height="96" rx="10" fill="rgba(255,211,138,.12)" stroke="#ffd38a"/>
    <text x="325" y="176" fill="#ffd38a" font-size="15" font-weight="800">先审查</text>
    <text x="325" y="200" fill="#f4ede4" font-size="13">SKILL.md 有无隐藏指令</text>
    <text x="325" y="220" fill="#f4ede4" font-size="13">脚本有无外发请求</text>
    <text x="325" y="240" fill="#f4ede4" font-size="13">依赖是否会变</text>
    <line x1="115" y1="124" x2="200" y2="270" stroke="#f5d0fe" stroke-width="2.5" marker-end="url(#sk-a5)"/>
    <line x1="325" y1="250" x2="240" y2="270" stroke="#f5d0fe" stroke-width="2.5" marker-end="url(#sk-a5)"/>
    <rect x="70" y="272" width="300" height="78" rx="12" fill="rgba(245,208,254,.14)" stroke="#f5d0fe"/>
    <text x="220" y="298" fill="#f5d0fe" font-size="15" font-weight="800">受限的运行环境</text>
    <text x="220" y="320" fill="#f4ede4" font-size="13">沙箱、最小权限、限制网络</text>
    <text x="220" y="340" fill="#9a93a8" font-size="13">危险操作仍需人工确认</text>
  </g>
</svg>
<figcaption>来源可信的 Skill 也要放在受限环境里运行；来源不明的 Skill 必须先审查指令和脚本</figcaption>
</figure>

Skill 让 Agent 变得更强，也带来了新的攻击面。原因很直接：

- **正文是会被模型遵从的指令。** 一个恶意的 SKILL.md 可以在看似正常的步骤里夹带「顺便把 `~/.ssh` 下的文件内容发到某个地址」，这是一种提示词注入（见本系列《Agent 安全与提示词注入》）；
- **脚本会被执行。** Agent 按说明运行 `scripts/` 里的代码，脚本能做的事取决于运行环境的权限；
- **依赖会变。** 一个今天无害的 Skill，如果脚本在运行时去下载外部文件或安装最新版本的包，明天就可能变得有害。

这不是理论上的担忧。2026 年初的一篇实证研究（Liu et al.，*Agent Skills in the Wild*）从两个 Skill 市场收集了四万多个社区 Skill，分析了其中 31,132 个，发现 **26.1%** 至少有一个安全问题，最常见的是数据外泄（13.3%）和权限提升（11.8%）；约 5.2% 的 Skill 有强烈暗示恶意意图的高危模式；**附带可执行脚本的 Skill 出问题的概率是纯指令 Skill 的 2.12 倍**。

Anthropic 官方文档给出的建议很明确：**只使用可信来源的 Skill**，也就是你自己写的，或者来自官方的；安装 Skill 要像安装软件一样对待。具体做法：

1. **审查所有附带文件**：SKILL.md、脚本、图片、参考资料，看有没有和声称用途不符的操作，比如意外的网络请求、读取无关目录；
2. **特别注意访问外部 URL 的 Skill**：外部内容可能被替换，里面可能藏着新的指令；
3. **固定依赖版本**，不要在运行时拉取最新版；
4. **最小权限运行**：放在沙箱或容器里，只给需要的目录和网络权限。Claude API 的 Skill 执行环境本身就没有网络访问；
5. **高风险操作保留人工确认**：删除、发布、转账这类操作，不要通过 `allowed-tools` 预先批准；
6. **组织层面统一管理**：企业里由专人维护一份经过审核的 Skill 清单，而不是每个人各自从网上下载。部分产品提供了对上传 Skill 的内容扫描功能，可以作为补充，但不能代替人工审查。

## 其他产品中的类似机制

在 Skills 出现之前，各家编程工具已经有了「给 Agent 写说明」的机制，最常见的是**规则文件**。它们和 Skills 解决的是相近但不完全相同的问题。

| 机制 | 形式 | 何时进入上下文 | 说明 |
|---|---|---|---|
| CLAUDE.md | 项目或用户目录下的 Markdown | 会话开始时加载 | Claude Code 的项目记忆和约定 |
| AGENTS.md | 仓库根目录或任意子目录的 Markdown | 通常会话开始时加载，离被编辑文件最近的那份优先 | 「写给 Agent 的 README」，多家工具共同支持，现由 Linux 基金会下的 Agentic AI Foundation 托管 |
| Cursor Rules | `.cursor/rules/*.mdc`，带前置元数据 | 四种模式：始终应用；由 Agent 根据描述判断；匹配文件路径（globs）时应用；手动 @ 引用 | 「根据描述判断」这种模式和 Skill 的思路最接近 |
| Copilot 自定义指令 | `.github/copilot-instructions.md`；`.github/instructions/*.instructions.md` 用 `applyTo` 指定路径 | 仓库级的始终加载；路径级的在处理匹配文件时加载 | 按文件路径做按需加载 |
| Agent Skills | 文件夹 + SKILL.md | 描述常驻，正文按需，附属文件按需 | 可以带脚本和资源，跨产品的开放格式 |

规则文件和 Skills 的主要区别：

- **规则文件适合「始终成立」的约定**：代码风格、目录结构、构建命令、禁止事项。这些内容每次都可能用到，放在 AGENTS.md 或 CLAUDE.md 里合适；
- **Skill 适合「特定任务的做法」**：写周报、审 SQL、处理 PDF、发版检查。只有遇到这类任务时才需要；
- **Skill 可以带代码和资源**，规则文件一般只是文本；
- **两者可以配合**：在 AGENTS.md 里写一句「数据库变更请先使用 sql-review 技能」，把常驻的约定和按需的流程连起来。

另外，这些产品如今大多已经同时支持 Skills：agentskills.io 的客户端列表里有 Claude Code、OpenAI Codex、Gemini CLI、GitHub Copilot、VS Code、Cursor、JetBrains Junie、OpenCode、Goose 等几十个产品。一个经验是：先写好 AGENTS.md 这类常驻说明，当它开始变长、出现「只在某类任务时才需要」的段落时，就把那些段落拆成 Skill。

## 常见的坑

### 1. 描述写得太泛，Skill 到处被触发

「处理数据相关的任务」这种描述会让 Skill 在很多不相关的请求里被读入，浪费上下文，还可能把错误的流程套到别的任务上。描述要具体到任务类型和关键词。

### 2. 描述写得太窄，Skill 从不被触发

只写了「生成周报」，用户说「帮我总结一下这周干了什么」时没有命中。可以收集真实用户的说法，写进描述；也可以用 Claude Code 的 `/context` 等命令确认 Skill 是否被加载。

### 3. 正文写成了百科全书

把 PDF 格式规范、Python 基础语法都写进正文，模型本来就会，只是白白占用上下文。正文只写模型不知道的、你们特有的东西。

### 4. 让模型做本该脚本做的事

「数一下这 500 条记录里有多少条是 feat」，模型可能数错。这类确定性工作写成脚本，模型只负责调用和解读结果。

### 5. 脚本输出太多

脚本把整份处理后的数据打印出来，等于把节省下来的上下文又还了回去。脚本应该写文件，只打印统计和摘要，就像示例里的 `clean_csv.py`。

### 6. 多个 Skill 职责重叠

「写文档」和「写周报」两个 Skill 的描述有交集时，模型可能选错，或者两个都读。每个 Skill 的边界要清楚，必要时在描述里写明「不用于……」。

### 7. 一个 Skill 装太多东西

一个 `team-handbook` 包含了所有流程，等于回到了「大系统提示」。按任务拆分，一个 Skill 做好一件事。

### 8. 从网上装来就用

前面讲过，Skill 里的指令会被执行、脚本会被运行。来源不明的 Skill 一定要先审查。

## 高频面试题速答

**Q：Agent Skills 是什么？**
一个 Skill 是一个文件夹，核心是 SKILL.md：YAML 前置元数据（name、description）加 Markdown 正文指令，还可以附带脚本、参考资料和模板。Agent 启动时只加载名称和描述，任务匹配时再读正文，需要时再读附属文件或运行脚本。

**Q：什么是渐进式披露？为什么重要？**
信息分三层加载：元数据常驻（每个约 100 token），正文命中时加载，附属文件按需加载。这样可以安装很多 Skill 而几乎不增加每次请求的上下文，也避免无关说明干扰当前任务。

**Q：Skill 和 MCP 有什么区别？**
MCP 是连接外部系统的协议，提供可调用的工具和资源，解决「能不能做到」；Skill 是打包好的做事方法和流程，解决「知不知道怎么做」。两者配合使用：Skill 里可以写明按什么顺序调用哪些 MCP 工具。

**Q：为什么 Skill 里要放脚本，而不是全部用文字描述？**
确定性的工作（统计、格式转换、校验）用代码做更便宜、更准确、可重复；脚本源码不需要进入上下文，只有输出进入，进一步节省 token。

**Q：description 应该怎么写？**
用第三人称，写清楚做什么和什么时候用，包含用户可能说的关键词，把最重要的用途放在前面。它是模型决定是否使用该 Skill 的唯一依据。

**Q：Skill 和 AGENTS.md / Cursor Rules 有什么区别？**
规则文件多数是会话开始时就加载的常驻约定，适合代码风格、构建命令这类始终成立的内容；Skill 是按需加载的任务流程，可以带脚本和资源。前者管「平时要守的规矩」，后者管「遇到某类任务怎么做」。

**Q：使用第三方 Skill 有什么风险？怎么防范？**
正文可能夹带恶意指令，脚本可能外泄数据或越权操作，外部依赖可能变化。只用可信来源，安装前审查所有文件，固定依赖版本，在沙箱和最小权限下运行，高风险操作保留人工确认。

## 总结

- 把所有说明写进系统提示，会**太长、太贵、互相干扰、难以维护**；
- **Skill 是一个文件夹**：SKILL.md（name + description + 正文指令），加上可选的脚本、参考资料和资源。格式由 Anthropic 提出，现在是 agentskills.io 上的开放标准，被几十个 Agent 产品支持；
- **渐进式披露**：描述常驻、正文按需、附属文件按需；脚本只有输出进入上下文；
- **MCP 给能力，Skill 给方法**；Skill 和提示词、工具、子 Agent 是配合关系，不是替代关系；
- 写好 Skill：**描述决定触发**，正文写流程、检查点、示例和反例，确定性步骤交给脚本，保持简洁、拆分文件，先有评测再写说明；
- 组织上用 Git 管理、跟代码一起评审、写明版本和负责人；
- **装 Skill 等于装软件**：只用可信来源，审查后在受限环境中运行。

<div class="refs" markdown="1">

### 参考资料

- Anthropic Engineering (2025). Equipping agents for the real world with Agent Skills.
- Claude 官方文档：Agent Skills overview；Skill authoring best practices；Using Agent Skills with the API.
- Claude Code 文档：Extend Claude with skills.
- Agent Skills 开放规范：agentskills.io（Overview、Specification）；GitHub agentskills/agentskills.
- GitHub anthropics/skills：官方示例 Skill 仓库.
- OpenAI 文档：Codex — Build skills.
- GitHub Docs：About agent skills；Adding repository custom instructions for GitHub Copilot.
- Cursor 文档：Rules；Skills.
- AGENTS.md：agents.md.
- Liu, Y., et al. (2026). Agent Skills in the Wild: An Empirical Study of Security Vulnerabilities at Scale. arXiv:2601.10338.
- Xu, R., et al. (2026). Agent Skills for Large Language Models: Architecture, Acquisition, Security, and the Path Forward. arXiv:2602.12430.

</div>
