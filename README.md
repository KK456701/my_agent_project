# 🔍 多智能体辩论式代码审查系统

基于 **LangChain + LangGraph** 的多 Agent 协作代码审查系统。

> 三个 AI Agent（🛡️安全 / ⚡性能 / 🏗️架构）独立审查代码 → 发现分歧 → 辩论裁决 → 生成报告。不是"各自审然后拼结果"，而是让 Agent 像真实团队一样互相 challenge。

---

## 🎯 核心亮点

### 多 Agent 辩论（不是分头干活）

```
Security Agent:  "这里要参数化查询，防止 SQL 注入"
Performance Agent: "但参数化在这个场景有 10% 开销"
Consensus Agent:  "折中方案：参数化 + statement cache，两者兼得"

→ 单 Agent 永远产生不了这种对抗性思考
```

### 生产级能力栈

| 层级 | 功能 | 技术 |
|:---:|------|------|
| 🔧 | **静态分析** | Ruff + Bandit（< 1s，不耗 LLM Token） |
| 📘 | **Skills 规范** | Markdown 团队规范，按文件类型 (.py/.ts/.go) 自动注入 |
| 🧠 | **审查记忆** | Markdown 零依赖知识库，动态签名表 + 关键词加权召回 Top-5 |
| 🧭 | **智能路由** | 关键文件 × 文件类型 × Commit 语义 三维决策引擎 |
| ⚔️ | **Agent 辩论** | Send API 并行 → 冲突检测 → Consensus 裁决 |
| 🔺 | **人工升级** | 辩论 3 轮僵局或置信度 < 0.6 → 升级人工 |
| 🤖 | **Agent-to-Agent** | 双格式输出：Markdown（人看）+ JSON Fixer Payload（下游 Agent 消费） |
| 🌐 | **GitHub 集成** | CLI / Webhook 自动触发 / PR 自动评论 |

---

## 🏗️ 完整架构

```
                          PR 提交 / 本地文件
                                │
              ┌─────────────────┼─────────────────┐
              ↓                 ↓                 ↓
         ┌─────────┐    ┌─────────────┐    ┌──────────┐
         │  Linter │    │   Skills    │    │  Memory  │
         │ Ruff    │    │ python_sec  │    │ patterns │
         │ Bandit  │    │ python_perf │    │ 召回Top-5│
         └────┬────┘    └──────┬──────┘    └────┬─────┘
              │   < 1s, 非 LLM  │               │
              └─────────────────┼───────────────┘
                                ↓
              ┌─────────────────────────────────┐
              │       智能路由 (smart_router)    │
              │  关键文件 + 文件类型 + Commit    │
              │  → fast / dual / full           │
              └──────────────┬──────────────────┘
                             ↓
         ┌───────────────────┼───────────────────┐
         ↓                   ↓                   ↓
   ┌──────────┐       ┌──────────┐       ┌──────────┐
   │ Security │       │Performanc│       │Architect │
   │  Agent   │       │  Agent   │       │  Agent   │
   └────┬─────┘       └────┬─────┘       └────┬─────┘
        │   LangGraph Send API 并行（3 次独立 LLM 调用）│
        └──────────────────┼──────────────────┘
                           ↓
                   ┌───────────────┐
                   │  冲突检测      │
                   │  行号重叠 →    │
                   │  同一代码区域  │
                   └───────┬───────┘
                           ↓
              ┌──── 有冲突? ──── 否 ──────────┐
              ↓ 是                            │
       ┌──────────────┐                       │
       │  辩论循环     │                       │
       │  Consensus    │                       │
       │  35 conflicts │                       │
       │  asyncio      │                       │
       │  .gather 并发 │                       │
       └──────┬───────┘                       │
              ↓                               │
    ┌── 共识? ── 是 ──────────────────────────┘
    ↓ 否
┌──────────┐
│  升级人工 │
│  max 3轮  │
└────┬─────┘
     │
     └────────────────────────────────────────┐
                                              ↓
                                    ┌──────────────────┐
                                    │  generate_report  │
                                    │  纯 Python 0 Token│
                                    └────────┬─────────┘
                                             │
                          ┌──────────────────┼──────────────────┐
                          ↓                                     ↓
                   ┌─────────────┐                      ┌──────────────┐
                   │  review.md  │                      │  fixer.json   │
                   │  人看        │                      │  下游Agent消费 │
                   │  42KB       │                      │  2KB          │
                   └─────────────┘                      └──────────────┘
```

### 数据流总结

```
PR 代码 ──→ Pre-processing ──→ 智能路由 ──→ 3 Agent 并行审查 ──→ 冲突辩论 ──→ 双格式输出
              (Linter+Skills      (1/2/3个   (各一次LLM调用,    (Consensus   (Markdown+JSON)
               +Memory, <1s)       Agent)     互不对话)          裁决)

Token 消耗分布:
  Pre-processing: 0 token（纯 Python/子进程）
  3 Agent 审查:   ~22K input tokens（并行，等最慢）
  辩论裁决:       ~2K/次 × 并发
  报告生成:       0 token（纯字符串拼接）
  ─────────────────────────
  总计:           ~25K tokens（128K 窗口绰绰有余）
```

---

## 🚀 快速开始

### 1. 创建虚拟环境

```bash
python -m venv venv
venv\Scripts\activate      # Windows
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
pip install ruff bandit    # Linter 工具
```

### 3. 配置

```bash
copy .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY
```

### 4. 运行

```bash
# Demo 模式（审查内置示例代码）
python app.py

# 审查任意 Python 文件
python app.py --file your_code.py

# 审查 GitHub PR
python app.py --pr https://github.com/user/repo/pull/42

# 指定 commit 语义（影响智能路由）
python app.py --file code.py --commit "hotfix: urgent bug fix"

# 启动 Web API（含 Webhook）
python app.py --serve

# 禁用流式输出
python app.py --no-stream
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
│       ├── linter_runner.py   # Ruff + Bandit 静态分析
│       └── github_tool.py     # GitHub API 封装
│
├── prompts/                   # Agent System Prompt
│   ├── security.md / performance.md / architecture.md / consensus.md
│
├── skills/                    # 团队编码规范（Markdown）
│   ├── python_security.md / python_performance.md / python_architecture.md
│
├── memory/                    # 审查记忆库（Markdown，自动积累）
│   ├── patterns/              # 问题模式（如 sql_injection.md）
│   └── reviews/               # 完整报告归档
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

## 💡 面试 FAQ

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

**Q: 生成的报告怎么用？能对接其他 Agent 吗？**
> 双格式输出。Markdown（review.md）给人看完整审查过程和辩论理由。JSON（fixer.json）给下游 Agent 消费，每个 issue 只有 file/lines/severity/fix 五个字段，按严重程度排序，Fixer Agent 直接应用修复指令。

**Q: 什么时候需要人工介入？**
> Consensus Agent 裁决为"僵局"（双方论据权重相当）且辩论 3 轮未共识，或置信度 < 0.6 时，自动升级。报告里用「🔺 需人工裁决」标记，附双方论据。

**Q: Linter 是 LangChain Tool 吗？**
> 当前是 Pre-processing 模式——审查前秒出结果、拼进 prompt，比 Tool Calling 更高效。确定性操作不需要 Agent 花 round-trip 去"决定"调不调。升级路径已预留。

---

## 📝 License

MIT
