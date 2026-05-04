"""
架构审查 Agent — 专注架构与可维护性
"""
import json
from src.agents.base import BaseReviewAgent
from langchain_core.output_parsers import StrOutputParser


class ArchitectureReviewAgent(BaseReviewAgent):
    """架构审查 Agent"""

    domain = "architecture"
    prompt_file = "architecture.md"

    async def review(self, pr_diff: str, pr_files: list[str]) -> list[dict]:
        """从架构角度审查代码"""
        messages = self._build_messages(pr_diff, pr_files)

        chain = self.llm | StrOutputParser()
        raw_response = await chain.ainvoke(messages)

        return self._parse_response(raw_response)

    @staticmethod
    def _parse_response(raw: str) -> list[dict]:
        try:
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
                f["domain"] = "architecture"
            return findings
        except json.JSONDecodeError:
            return [{"domain": "architecture", "error": "解析失败", "raw": raw[:500]}]
