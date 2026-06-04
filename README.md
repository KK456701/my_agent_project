# 🔍 多智能体 PR 代码审查系统

基于 **LangChain + LangGraph + CodeGraph** 的 GitHub PR 自动审查系统。

> 四个 AI Agent（🛡️安全 / ⚡性能 / 🏗️架构 / 🔗关联性）并行审查 PR，从多维度发现代码问题。

---

## 🎯 定位

- ✅ 对 GitHub PR 进行自动化审查（`--pr`）
- ✅ Webhook 模式下 PR 创建即自动审查
- ✅ `--file` 仅用于本地测试
- ❌ 不是 IDE 插件，不是代码格式化工具

---

## 🏗️ 架构

```
                        GitHub PR / 本地文件
                              │
                    ┌─────────┴─────────┐
                    │  ① 智能路由        │
                    │  关键文件×类型     │
                    │  ×Commit语义      │
                    │  → fast/dual/full │
                    └─────────┬─────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
   ┌──────────┐        ┌──────────┐        ┌──────────┐
   │ 🛡️ 安全   │        │ ⚡ 性能   │        │ 🏗️ 架构   │
   │ Agent    │        │ Agent    │        │ Agent    │
   └──────────┘        └──────────┘        └──────────┘
         │                    │                    │
         │    LangGraph Send API 并行执行          │
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │  ② 关联性全链路    │  ← Impact Agent
                    │  DeepSeek筛选     │
                    │  → CodeGraph查    │
                    │  → 读受影响文件   │
                    │  → 关联性审查     │
                    └─────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    │  ③ 生成报告        │
                    │  按严重度排序      │
                    └────────────────────┘
```

---

## 🔗 关联性分析全链路

```
PR diff
  │
  ▼ ① DeepSeek 分类器
  skip 跳过 | light 轻量 | deep 深挖
  │
  ▼ ② CodeGraph CLI (deep 标记的符号)
  codegraph callers → 找到调用方
  codegraph impact  → 分析影响半径
  │
  ▼ ③ 读取受影响文件完整源码
  变更文件 + 跨文件依赖文件
  │
  ▼ ④ Impact Agent 审查
  跨文件调用、委托层、命名冲突、影响半径
```

### 每个 Agent 内部 5 层漏斗

```
代码片段
  │
  ▼ Linter (Ruff+Bandit)  → 0 Token, <1s
  ▼ Skills Cache (YAML)   → 0 Token, <1ms, 29条规则
  ▼ Skills 规范注入        → 按文件类型
  ▼ Memory 语义召回        → DeepSeek 选相关模式
  ▼ LLM 审查 (DeepSeek)   → AI 深度分析
```

---

## ⚡ 审查能力栈

| 层级 | 功能 | 说明 |
|:---:|------|------|
| 🔧 | Linter 静态分析 | Ruff+Bandit, <1s, 0 Token |
| ⚡ | Skills Cache | 确定性匹配直接跳过 LLM, 29 条规则 |
| 📘 | Skills 规范注入 | 按文件类型注入团队规范 |
| 🧠 | 审查记忆 | DeepSeek 语义召回 + Markdown 积累 |
| 🧭 | 智能路由 | 关键文件 × 文件类型 × Commit 语义 |
| 🔗 | 关联性分析 | DeepSeek筛选→CodeGraph→受影响文件→审查 |
| 🤖 | 4 Agent 并行 | 安全+性能+架构+关联性, Send API 并行 |

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
#   OPENAI_API_KEY=sk-xxx            # DeepSeek API Key
#   OPENAI_API_BASE=https://api.deepseek.com
#   MODEL_NAME=deepseek-chat
#   GITHUB_TOKEN=ghp_xxx             # GitHub Token
#   PROJECT_ROOT=F:\PRtest\testagentPR  # 本地项目路径
```

### 3. 安装 CodeGraph

```powershell
# Windows PowerShell
irm https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.ps1 | iex

# 索引项目
cd F:\PRtest\testagentPR
codegraph init -i
```

### 4. 审查 PR

```bash
# 一行命令审查 GitHub PR
python app.py --pr https://github.com/用户/仓库/pull/123

# 本地测试
python app.py --file demo/sample_pr.py

# Webhook 服务
python app.py --serve
```

---

## 📂 项目结构

```
my-Agentproject/
├── app.py                      # 主入口 CLI
├── app_web.py                  # FastAPI + GitHub Webhook
├── config.py                   # 全局配置
├── .env                        # 环境变量
│
├── src/
│   ├── graph/
│   │   ├── state.py            # LangGraph State
│   │   └── debate_graph.py     # 核心审查图 (路由→审查→报告)
│   ├── agents/
│   │   ├── base.py             # Agent 基类
│   │   ├── security_agent.py   # 🛡️ 安全审查
│   │   ├── performance_agent.py # ⚡ 性能审查
│   │   ├── architecture_agent.py # 🏗️ 架构审查
│   │   └── impact_agent.py     # 🔗 关联性审查
│   └── tools/
│       ├── code_analyzer.py    # Diff 解析 + 截断
│       ├── smart_router.py     # 三维度智能路由
│       ├── review_memory.py    # DeepSeek 语义记忆(v2)
│       ├── skills_loader.py    # Skills 加载
│       ├── linter_runner.py    # Ruff + Bandit
│       ├── pattern_matcher.py  # Skills Cache 匹配
│       ├── impact_classifier_llm.py # 变更分级(DeepSeek版)
│       ├── quality_validator.py    # 质量校验
│       └── github_tool.py      # GitHub API
│
├── prompts/                    # Agent System Prompt
│   ├── security.md / performance.md / architecture.md / impact.md
│
├── skills/                     # 多语言团队编码规范
│   ├── python_security.md / python_performance.md
│   ├── go_security.md / go_performance.md / go_architecture.md
│   └── javascript_security.md / javascript_performance.md
│
├── memory/                     # 审查记忆库
│   └── patterns/               # 问题模式 (如 sql_injection.md)
│
├── reports/                    # 审查报告存档
├── demo/                       # 测试代码
└── scripts/                    # 工具脚本
```

---

## 📊 审查数据流

```
PR diff → 智能路由 → 4 Agent并行 → 汇聚 → 报告

Token 消耗:
  Linter / Cache / Memory:  0 token
  4 Agent 审查:             ~30K input (并行)
  关联性筛选 (DeepSeek):    ~500 token
  CodeGraph CLI:             0 token (本地子进程)
  报告生成:                  0 token
  ─────────────────────────
  总计:                     ~30K tokens
```

### 报告示例

```
📊 总览
PR: My feature prtest
审查模式: full（4 Agent）
总问题: 24（🔴4 🟠8 🟡5 🟢4 💡3）

🔴 Critical
  parseToken 方法重复定义 — JwtUtil.java:32-42

🟠 High  
  不必要的委托层：generateToken → JwtUtil.createToken
  不必要的委托层：parseToken → JwtUtil.parseToken

🟡 Medium
  UserContext 职责膨胀，违反单一职责原则
```

---

## 🔧 关键设计

| 设计 | 说明 |
|------|------|
| **4 Agent 并行** | LangGraph Send API 图级并行, 互不阻塞 |
| **关联性全链路** | DeepSeek筛选 → CodeGraph结构 → 文件源码 → Impact审查 |
| **记忆语义召回** | DeepSeek 从 101 个模式中选出相关案例注入 prompt |
| **Skills Cache** | 29 条确定性 YAML 规则, 命中后直接跳过 LLM |
| **三级路由** | fast(2 Agent) / dual(3) / full(4), 按 PR 规模自动选 |

---

## 📝 License

MIT
