"""
GitHub PR 工具 — 对接 GitHub API

注意：这需要 GITHUB_TOKEN 环境变量
"""
import os
import httpx
from typing import Optional


class GitHubPRTool:
    """
    GitHub PR 操作工具
    
    用途：
    - 获取 PR 的 diff 内容
    - 在 PR 上发表评论（审查意见）
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DebateReviewBot/1.0",
        }

    async def get_pr_diff(
        self, owner: str, repo: str, pr_number: int
    ) -> dict:
        """
        获取 PR 的详细信息和 diff
        
        Returns:
            {"title": "PR 标题", "diff": "diff 内容", "files": ["file1.py", ...]}
        """
        async with httpx.AsyncClient() as client:
            # 获取 PR 信息
            pr_resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self.headers,
            )
            pr_resp.raise_for_status()
            pr_data = pr_resp.json()

            # 获取 diff（使用 Accept: diff header）
            diff_resp = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers={**self.headers, "Accept": "application/vnd.github.v3.diff"},
            )
            diff_resp.raise_for_status()

            return {
                "title": pr_data.get("title", ""),
                "body": pr_data.get("body", "") or "",
                "diff": diff_resp.text,
                "files": [f["filename"] for f in pr_data.get("changed_files", [])],
            }

    async def post_review_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> dict:
        """
        在 PR 上发表一条评论
        
        Args:
            owner: 仓库所有者
            repo: 仓库名
            pr_number: PR 编号
            body: 评论内容（支持 Markdown）
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments",
                headers=self.headers,
                json={"body": body},
            )
            resp.raise_for_status()
            return resp.json()

    async def post_review(
        self, owner: str, repo: str, pr_number: int, body: str, event: str = "COMMENT"
    ) -> dict:
        """
        创建一条正式的 PR Review
        
        Args:
            event: "APPROVE" | "REQUEST_CHANGES" | "COMMENT"
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
                headers=self.headers,
                json={"body": body, "event": event},
            )
            resp.raise_for_status()
            return resp.json()
