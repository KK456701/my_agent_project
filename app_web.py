"""
FastAPI Web 服务 — 提供 REST API 接口

启动: python app.py --serve
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.graph.debate_graph import debate_graph
from src.graph.state import DebateState
from src.tools.code_analyzer import parse_diff_to_files
from config import config

app = FastAPI(
    title="多智能体辩论式代码审查",
    description="基于 LangGraph 的多智能体代码审查系统",
    version="1.0.0",
)


class ReviewRequest(BaseModel):
    """审查请求"""
    title: str = "代码审查"
    diff: str
    mode: str = "auto"  # auto | fast | full


class ReviewResponse(BaseModel):
    """审查响应"""
    mode: str
    debate_rounds: int
    total_issues: int
    conflicts_resolved: int
    conflicts_escalated: int
    report: str


@app.get("/", response_class=HTMLResponse)
async def root():
    """首页 — 简单的使用说明"""
    return """
<!DOCTYPE html>
<html>
<head><title>多智能体辩论式代码审查</title></head>
<body style="font-family: sans-serif; max-width: 800px; margin: 50px auto;">
    <h1>🔍 多智能体辩论式代码审查</h1>
    <p>基于 LangGraph + LangChain，多个 AI Agent 从安全、性能、架构角度审查代码，并通过辩论达成共识。</p>
    <h2>API 端点</h2>
    <ul>
        <li><code>POST /review</code> — 提交 diff 进行审查</li>
        <li><code>GET /health</code> — 健康检查</li>
        <li><a href="/docs">/docs</a> — Swagger 文档</li>
    </ul>
    <h2>示例</h2>
    <pre>
curl -X POST http://localhost:8000/review \\
  -H "Content-Type: application/json" \\
  -d '{"title":"login fix", "diff":"...git diff..."}'
    </pre>
</body>
</html>
"""


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/review", response_model=ReviewResponse)
async def review(req: ReviewRequest):
    """提交代码审查"""
    try:
        config.validate()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    files = parse_diff_to_files(req.diff)

    # 手动设置 mode
    if req.mode == "full":
        domains = ["security", "performance", "architecture"]
    else:
        domains = []

    initial_state: DebateState = {
        "pr_title": req.title,
        "pr_diff": req.diff,
        "pr_files": files,
        "review_mode": "",
        "active_domains": domains,
        "security_findings": [],
        "performance_findings": [],
        "architecture_findings": [],
        "conflicts": [],
        "debate_round": 0,
        "debate_history": [],
        "final_report": "",
        "fixer_payload": "",
        "escalated": False,
        "total_tokens": 0,
        "error": "",
    }

    final_state = await debate_graph.ainvoke(initial_state)

    # 统计
    all_findings = (
        final_state.get("security_findings", [])
        + final_state.get("performance_findings", [])
        + final_state.get("architecture_findings", [])
    )
    conflicts = final_state.get("conflicts", [])
    resolved = sum(1 for c in conflicts if c.get("status") == "resolved")
    escalated = sum(1 for c in conflicts if c.get("status") == "escalated")

    return ReviewResponse(
        mode=final_state.get("review_mode", "auto"),
        debate_rounds=final_state.get("debate_round", 0),
        total_issues=len(all_findings),
        conflicts_resolved=resolved,
        conflicts_escalated=escalated,
        report=final_state.get("final_report", ""),
    )


# ============================================================
# GitHub Webhook — PR 创建时自动触发审查
# ============================================================

import hmac
import hashlib
import os
import asyncio
from fastapi import Request, BackgroundTasks

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")


def verify_signature(payload: bytes, signature: str) -> bool:
    """验证 GitHub Webhook 签名"""
    if not WEBHOOK_SECRET:
        return True  # 未配置 secret 则跳过验证
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def auto_review_pr(owner: str, repo: str, pr_number: int, title: str, body: str):
    """
    后台任务：自动审查 PR 并评论结果
    
    流程：
    1. 从 GitHub 拉取 PR diff
    2. 运行多智能体审查
    3. 把结果评论到 PR 上
    """
    from src.tools.github_tool import GitHubPRTool

    github = GitHubPRTool()
    try:
        # 1. 获取 PR diff
        pr_data = await github.get_pr_diff(owner, repo, pr_number)

        # 2. 运行审查
        from app import review_diff
        report = await review_diff(pr_data["diff"], title, commit_message=body, no_stream=True)

        # 3. 裁剪报告（GitHub 评论有长度限制，取前 6000 字）
        short_report = report[:6000]
        if len(report) > 6000:
            short_report += "\n\n> ⚠️ 报告被截断，完整内容见本地 reports/ 目录"

        # 4. 作为 PR Review 评论
        comment = f"## 🤖 多智能体审查报告\n\n{short_report}\n\n---\n*由 Security + Performance + Architecture 三个 Agent 协作生成*"
        await github.post_review(owner, repo, pr_number, comment, event="COMMENT")

        print(f"✅ 自动审查完成: {owner}/{repo}#{pr_number}")

    except Exception as e:
        print(f"❌ 自动审查失败: {e}")


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    接收 GitHub Webhook 事件

    在 GitHub 仓库 Settings → Webhooks 中配置：
    - Payload URL: https://你的服务器/webhook/github
    - Content type: application/json
    - Events: Pull requests

    用法示例：
    1. 启动服务: python app.py --serve
    2. 用 ngrok 暴露到公网: ngrok http 8000
    3. 在 GitHub 仓库添加 Webhook: https://ngrok地址/webhook/github
    """
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    # 验证签名
    if not verify_signature(payload, signature):
        return {"error": "签名验证失败"}, 403

    event = request.headers.get("X-GitHub-Event", "")
    data = await request.json()

    # 只处理 PR 打开和同步事件
    if event == "pull_request" and data.get("action") in ("opened", "synchronize"):
        pr = data["pull_request"]
        owner = data["repository"]["owner"]["login"]
        repo = data["repository"]["name"]
        pr_number = pr["number"]
        title = pr["title"]
        body = pr.get("body", "") or ""

        # 后台执行审查（不阻塞 Webhook 响应）
        background_tasks.add_task(auto_review_pr, owner, repo, pr_number, title, body)

        return {
            "status": "accepted",
            "message": f"开始审查 {owner}/{repo}#{pr_number}: {title}",
        }

    return {"status": "ignored", "event": event}
