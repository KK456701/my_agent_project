# 🔍 多智能体辩论式 PR 审查系统

基于 **LangChain + LangGraph** 的 GitHub PR 自动审查系统。

> 三个 AI Agent（🛡️安全 / ⚡性能 / 🏗️架构）独立审查 PR diff → 发现分歧 → 辩论裁决 → 生成报告。让每个 PR 在合并前都经过多维度自动审查。

---

## 🎯 定位

**这是一个 PR 审查工具，不是通用代码分析器。**

- ✅ 对 GitHub PR 进行自动化审查（`--pr`）
- ✅ Webhook 模式下 PR 创建即自动审查
- ✅ `--file` 仅用于本地测试，方便开发调试
- ❌ 不是 IDE 插件，不是代码格式化工具

---

## 🎯 核心亮点

### 多 Agent 辩论（不是分头干活）

```
Security Agent:  "这里要参数化查询，防止 SQL 注入"
Performance Agent: "但参数化在这个场景有 10% 开销"
Consensus Agent:  "折中方案：参数化 + statement cache，两者兼得"

→ 单 Agent 永远产生不了这种对抗性思考
```

### 审查能力栈

| 层级 | 功能 | 说明 |
|:---:|------|------|
| 🔧 | **Linter 静态分析** | 多语言支持，< 1s，0 Token |
| ⚡ | **Skills Cache** | 确定性命中直接跳过 LLM，29 条跨语言规则 |
| 📘 | **Skills 规范** | 按文件类型自动注入团队规范 |
| 🧠 | **审查记忆** | Markdown 知识库自动积累，越审越准 |
| 🧭 | **智能路由** | 关键文件 × 文件类型 × Commit 语义 |
| ⚔️ | **Agent 辩论** | 对抗性冲突 → Consensus 裁决，正交发现直出 |
| 🔺 | **人工升级** | 辩论 3 轮僵局 / 置信度 < 0.6 → 升级人工 |

---

## 🏗️ 完整架构

```
                          PR 提交
                            │
              ┌─────────────┼─────────────┐
              ↓             ↓             ↓
         ┌─────────┐  ┌──────────────┐  ┌──────────────────┐
         │  Linter │  │ Skills Cache │  │  Memory (召回)    │
         │ 多语言  │  │ 确定性命中    │  │ 扫描→签名表      │
         │ < 1s    │  │ 跳过 LLM      │  │ Top-5 注入       │
         └────┬────┘  └──────┬───────┘  └────────┬─────────┘
              │ 0 Token       │ 0 Token          ↑
              └───────────────┼──────────────────┘
                              ↓
              ┌───────────────────────────────┐
              │       智能路由                 │
              │  关键文件 + 类型 + Commit       │
              │  → fast / dual / full          │
              └──────────────┬────────────────┘
                             ↓
         ┌───────────────────┼───────────────────┐
         ↓                   ↓                   ↓
   ┌──────────┐       ┌──────────┐       ┌──────────┐
   │ Security │       │Performanc│       │Architect │
   │  Agent   │       │  Agent   │       │  Agent   │
   └────┬─────┘       └────┬─────┘       └────┬─────┘
        │   LangGraph Send API 并行                │
        └──────────────────┼──────────────────┘
                           ↓
                   ┌──────────────────┐
                   │  冲突检测         │
                   │  规则优先+语义兜底 │
                   │  修复互斥是主判据  │
                   └───────┬──────────┘
                           ↓
         ┌──── 修复互斥? ──── 否 ──→ 正交标注 ──────┐
         ↓ 是 (修复方案打架)                          │
  ┌──────────────┐                                   │
  │  辩论循环     │                                   │
  │  Consensus    │                                   │
  │  max 3 轮     │                                   │
  │  asyncio.gather│                                  │
  └──────┬───────┘                                   │
         ↓                                           │
   ┌── 共识? ── 是 ─────────────────────────────────┘
   ↓ 否
┌──────────┐
│  升级人工 │
└────┬─────┘
     └───────────────────────────────────┐
                                         ↓
                              ┌──────────────────┐
                              │  generate_report  │
                              │  + 质量校验       │
                              └────────┬─────────┘
                                       ↓
                              ┌─────────────────┐
                              │  reports/xxx.md  │
                              │  按严重程度排序   │
                              └────────┬────────┘
                                       ↓
                              ┌─────────────────┐
                              │  记忆归档        │
                              │  patterns/*.md   │
                              └─────────────────┘
```

### 记忆库生命周期

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  审查前 (召回) — 0 Token                                     │
│  ┌─────────────┐     ┌─────────────┐    ┌──────────────┐    │
│  │ memory/      │ ──→ │ _build_     │ ──→│ recall_      │    │
│  │ patterns/    │     │ dynamic_    │    │ knowledge()  │    │
│  │ *.md         │     │ signatures()│    │ Top-5 注入   │    │
│  └─────────────┘     │ 文件名+内容  │    │ Agent prompt │    │
│                      │ 提取关键词    │    └──────────────┘    │
│                      └─────────────┘                        │
│                                                              │
│  审查后 (入库) — 0 Token                                     │
│                                                              │
│  generate_report() 产生报告文本                               │
│       │                                                     │
│       ├──→ _save_report() ──→ reports/xxx.md  (给人看)      │
│       │                                                     │
│       └──→ save_review_to_memory(report)                    │
│                │                                            │
│                └──→ 正则提取 finding（标题/文件/行号/建议）   │
│                         │                                   │
│                         ├── 已知模式 → _update_pattern()     │
│                         │              审查次数+1 + 追加案例  │
│                         │                                   │
│                         └── 新问题   → _create_pattern()     │
│                                       新建 .md 文件          │
│                                                              │
│  报告和 Pattern 独立存储，互不依赖：                           │
│  - reports/     = 完整审查报告（给人看，可删除不影响系统）     │
│  - patterns/    = 结构化知识（给 Agent 用，越审越准）         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 数据流总结

```
PR diff ──→ 三层过滤 ──→ 智能路由 ──→ 3 Agent 并行 ──→ 冲突检测 ──→ reports/xxx.md
          (Linter+Cache       (1/2/3个    (各一次LLM      (规则优先+      (按严重程度
           +Memory, <1s)       Agent)      调用,互不对话)    语义兜底)      排序+质量校验)

Token 消耗分布:
  ① Linter / Cache / Memory:  0 token（纯 Python/子进程/正则）
  ② 3 Agent 审查:              约 22K input tokens（并行，等最慢）
  ③ 冲突检测（语义精排）:        0 token（本地 CPU embedding，< 10ms/对）
  ④ 辩论裁决:                   仅在修复互斥时触发，约 2K/次 × 并发
  ⑤ 报告 + 质量校验:            0 token（纯字符串拼接）
  ─────────────────────────
  总计:          约 25K tokens（辩论触发时额外 2-6K）
```

### 冲突检测详解

```
                    fa, fb (不同 domain, 同文件)
                              │
              ┌───────────────┴───────────────┐
              │  Step 1: 同一问题？             │
              │  embedding 描述相似度 > 0.85    │
              │  模型不可用 → 保守: 不同问题     │
              └───────────────┬───────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ↓ 同一问题                              ↓ 不同问题
  ┌─────────────────┐                ┌─────────────────────┐
  │ Step 1.5: 互斥？ │                │ Step 2: 修复互斥？    │
  │                 │                │ (跨行语义冲突)        │
  │ 规则优先(0Token) │                │                     │
  │ 语义兜底         │                │ 互斥 → 🔴 对抗       │
  │                 │                │ 不互斥 → Step 3      │
  │ 互斥 → 🔴 对抗   │                │ 灰色   → Step 3      │
  │ 不互斥 → 🟢 正交 │                └─────────┬───────────┘
  └─────────────────┘                          │
                                   ┌───────────┴───────────┐
                                   │ Step 3: 行号重叠？      │
                                   │                       │
                                   │ 否 → 全局语义兜底      │
                                   │ 是 → severity差/关键词 │
                                   │      交集/语义验证     │
                                   │ 默认 → 🟢 正交(保守)   │
                                   └───────────────────────┘
```

**核心原则**：修复方案互斥是主判据，位置/语义只是辅助信号。只有修复方案真正打架的才值得辩论。

**为什么规则优先**：embedding 模型按主题算相似度，"删除缓存"和"加 TTL 缓存"都含"缓存"词 → 相似度 0.999，分不出矛盾。规则先跑补这个盲区。

**测试验证**：`python demo/test_conflict_pipeline.py` 可绕过 LLM Agent，用预制矛盾 findings 验证整条管线。

---

## 🚀 快速开始

### 1. 环境准备

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install ruff bandit
```

### 2. 配置

```bash
copy .env.example .env
# 编辑 .env:
#   OPENAI_API_KEY=sk-xxx        # DeepSeek / OpenAI Key
#   GITHUB_TOKEN=ghp_xxx          # GitHub Personal Access Token（勾选 repo）
```

### 3. 审查 PR

```bash
# 一行命令审查 GitHub PR
python app.py --pr https://github.com/用户/仓库/pull/123

# 指定 commit 语义（影响路由策略）
python app.py --pr https://github.com/用户/仓库/pull/123 --commit "hotfix: urgent"

# 启动 Webhook 服务（PR 创建时自动审查）
python app.py --serve
```

### 4. 本地测试（不需要 PR）

```bash
# Demo 模式
python app.py

# 审查指定文件
python app.py --file demo/sample_pr.py
```

---

## 📂 项目结构

```
my-Agentproject/
├── app.py                     # 主入口 CLI（流式输出 + 多模式）
├── app_web.py                 # FastAPI + GitHub Webhook
├── config.py                  # 全局配置
├── .env / .env.example        # 环境变量
│
├── src/
│   ├── graph/
│   │   ├── state.py           # LangGraph State（TypedDict）
│   │   └── debate_graph.py    # 核心辩论图（7 节点 + 条件路由）
│   ├── agents/
│   │   ├── base.py            # Agent 基类（记忆注入 + Skills 注入）
│   │   ├── security_agent.py  # 🛡️ 安全审查
│   │   ├── performance_agent.py
│   │   ├── architecture_agent.py
│   │   └── consensus_agent.py # ⚖️ 辩论裁决
│   └── tools/
│       ├── code_analyzer.py   # Diff 解析 + 截断 + 冲突检测
│       ├── smart_router.py    # 三维度智能路由
│       ├── review_memory.py   # Markdown 审查记忆（召回 + 归档）
│       ├── skills_loader.py   # Skills 体系（按文件类型加载）
│       ├── linter_runner.py   # Ruff + Bandit (多语言)
│       ├── pattern_matcher.py  # Skills Cache 确定性匹配引擎
│       ├── semantic_reranker.py # 语义精排（RAG Rerank）— 可选
│       ├── quality_validator.py # 0 Token 质量校验（语法/路径/敏感信息/一致性）
│       └── github_tool.py     # GitHub API 封装
│
├── prompts/                   # Agent System Prompt
│   ├── security.md / performance.md / architecture.md / consensus.md
│
├── skills/                    # 多语言团队编码规范（Python/Go/JS/TS）
│   ├── python_security.md / python_performance.md / python_architecture.md
│   ├── go_security.md / go_performance.md / go_architecture.md
│   └── javascript_security.md / javascript_performance.md / typescript_best_practices.md
│
├── memory/                    # 审查记忆库（Markdown，自动积累）
│   └── patterns/              # 问题模式（如 sql_injection.md）
│
└── demo/
    └── sample_pr.py           # 故意包含问题的 Demo 代码
```

---

## ⚡ 性能优化

| 优化项 | 效果 |
|--------|------|
| 并行辩论（asyncio.gather） | 辩论从串行数秒/个 → 并发秒级完成 |
| diff 截断（去噪保留变更行） | Token ↓ 30% |
| 信号量控制并发 | 防 API 限流 |
| 分级路由（小改动走快速通道） | 70% PR 省 2/3 Token |
| Linter 预处理（非 LLM） | 静态问题秒出 |

---

## 🔺 Human-in-the-Loop：什么情况需要人工

### 触发条件

| 条件 | 说明 | 代码位置 |
|------|------|---------|
| **Consensus 裁决"僵局"** | 两个 Agent 的论据权重相当，AI 无法判断谁对 | `debate_round()` stalemate 分支 |
| **达到最大辩论轮次** | 辩论 3 轮仍未共识 → 自动升级 | `MAX_DEBATE_ROUNDS = 3` |
| **置信度不足** | Consensus Agent 判决 confidence < 0.6 | `prompts/consensus.md` 约定 |

### 典型场景

```
Security: "必须参数化查询，这是 SQL 注入"        ← 安全优先
Performance: "参数化会导致索引失效，QPS 降 30%"   ← 性能优先
Consensus: "双方都有道理，我无法判断业务优先级"    ← stalemate
    ↓ 3 轮后
→ 📋 升级给人工，附双方论据："请确认是安全优先还是性能优先"
```

### 报告中的体现

```markdown
### 🔺 需人工裁决 (2 个)

- 文件: src/auth.py (行 42-45)
  - 各方立场 (辩论 3 轮后未达成共识):
    - security: SQL 注入风险，必须用参数化查询
    - performance: 当前索引策略下参数化会降 30% QPS
```

> ⚡ 不是"AI 无能"，而是"AI 知道什么时候该让人类拍板"——这是负责任的设计。

---

## 💡 QA

**Q: 这个多智能体和传统大模型对话有什么区别？**
> 不是多轮对话！每个 Agent 是 LangGraph 编排下的一次独立 LLM 调用，用不同的 System Prompt 塑造不同"人格"。Agent 之间不直接通信，上下文通过 LangGraph State 在节点间传递。3 个 Agent 审查是 Send API 图级并行，辩论裁决是 asyncio.gather 并发。

**Q: 为什么用多智能体而不是单 Agent？**
> 代码审查的本质是**权衡**——安全、性能、可读性经常互相冲突。单 Agent 面对冲突会"和稀泥"，多 Agent 辩论让不同视角正面交锋，产生单大脑永远不会有的对抗性思考。

**Q: Token 消耗会不会很高？**
> 做了四级优化：分级路由（小 PR 走快速通道）、diff 截断、并行辩论、Linter 预处理（静态问题不耗 LLM）。优化后单 PR 成本控制在数美分级别。

**Q: 记忆系统怎么做的？**
> 不用向量数据库，用 Markdown 文件——类似 Claude Code 的 Memory。每次审查后自动归档到 `memory/patterns/`，下次相似代码关键词匹配 + 加权评分召回。零依赖、人类可读、Git 可追踪。

**Q: 模式文件多了会影响性能吗？**
> 不会。关键词匹配是 O(n) 内存操作，每个文件只读前 1500 字符。注入有双重硬限制：最多 Top-5 个模式 + 总字符 ≤ 5000。25 个文件和 10000 个文件对 LLM 的 Token 消耗完全一样。

**Q: 生成的报告怎么用？**
> 一份 review.md，按严重程度排序（critical → info），每个问题标注来源（Cache/Agent）和修复建议。PR 审查完后直接发给开发者即可。

**Q: 什么时候需要人工介入？**
> Consensus Agent 裁决为"僵局"（双方论据权重相当）且辩论 3 轮未共识，或置信度 < 0.6 时，自动升级。报告里用「🔺 需人工裁决」标记，附双方论据。

**Q: Skills Cache、Linter、Memory 三者有什么区别？**
> Linter（外部程序，预定义规则）只给"可疑"标记；Skills Cache（内部 YAML 规则，人确认过的）命中直接出修复方案并跳过 LLM；Memory（机器自动积累）有误召回风险，注入 prompt 让 Agent 二次确认。递进关系：Linter 查语法 → Cache 查确定模式 → Agent 查剩下的。

**Q: 冲突检测怎么判断对抗 vs 正交？**
> 核心判据：**修复方案是否互斥**。分三步——Step 1: 描述语义相似度判断是否同一问题；Step 2: 修复互斥检测（规则优先，embedding 兜底）；Step 3: 行号重叠 + 规则兜底。修复方案打架（如"删缓存" vs "加 TTL 缓存"）→ 对抗送辩论；同一问题不同视角 → 正交标注「🔗 交叉发现」。0 Token，纯 Python + 本地 embedding。

**Q: 为什么规则优先而不是语义优先？**
> embedding 模型按主题算相似度，"删除缓存"和"加 TTL 缓存"都含"缓存"词 → 相似度 0.999，分不出矛盾。规则先跑补这个盲区——硬编码互斥词对（如 bcrypt vs SHA256、参数化 vs f-string、删缓存 vs 保留缓存）先命中返回，未命中才走 semantic 兜底。参见 `demo/test_conflict_pipeline.py`。

**Q: 为什么实际审查中对抗性冲突很少？**
> LLM Agent 天然倾向给出平衡方案而非极端立场。即使代码有明显的 trade-off（如"旧加密库有 CVE vs 替换后性能降 15 倍"），Agent 也会给出"升级 + 加硬件加速"之类的折中建议，而非对立方案。这不是 bug——好的审查就应该是理性折中的。辩论机制是安全网，不是日常功能。测试管道完整性的方式：`python demo/test_conflict_pipeline.py`。

**Q: Linter 是 LangChain Tool 吗？**
> 当前是 Pre-processing 模式——审查前秒出结果、拼进 prompt，比 Tool Calling 更高效。确定性操作不需要 Agent 花 round-trip 去"决定"调不调。升级路径已预留。

---

## 📝 License

MIT
