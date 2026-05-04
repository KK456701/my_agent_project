"""
安全审查 Agent — 专注安全漏洞检测
"""
import json
from src.agents.base import BaseReviewAgent
from langchain_core.output_parsers import StrOutputParser


class SecurityReviewAgent(BaseReviewAgent):
    """安全审查 Agent"""

    domain = "security"
    prompt_file = "security.md"

    async def review(self, pr_diff: str, pr_files: list[str]) -> list[dict]:
        """从安全角度审查代码"""
        messages = self._build_messages(pr_diff, pr_files)

        chain = self.llm | StrOutputParser()
        raw_response = await chain.ainvoke(messages)

        return self._parse_response(raw_response)

    @staticmethod
    def _parse_response(raw: str) -> list[dict]:
        """解析 LLM 返回的 JSON，提取 findings"""
        try:
            # 容错：LLM 可能包裹在 ```json 代码块中
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()

            data = json.loads(raw)
            findings = data.get("findings", [])
            for f in findings:
                f["domain"] = "security"  # 标记领域
            return findings
        except json.JSONDecodeError:
            return [{"domain": "security", "error": "解析失败", "raw": raw[:500]}]
