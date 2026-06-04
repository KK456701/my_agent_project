"""
Impact Agent — 代码图谱驱动的关联性审查

审查重点：
  1. 变更函数的调用方是否兼容（签名、返回值、异常）
  2. 新增符号是否与现有符号冲突（命名、签名重载）
  3. 跨文件的隐式依赖是否被破坏（import 链、全局状态）
  4. 变更的影响半径是否合理（高扇出函数变更风险大）
"""
import json
from src.agents.base import BaseReviewAgent
from langchain_core.messages import SystemMessage, HumanMessage


class ImpactReviewAgent(BaseReviewAgent):
    """关联性影响审查 Agent"""

    domain = "impact"
    prompt_file = "impact.md"

    async def review(
        self,
        pr_diff: str,
        pr_files: list[str],
        full_file_context: str = "",
        inject_memory: bool = True
    ) -> list[dict]:
        """
        审查 PR 的关联性风险

        Args:
            pr_diff: PR 的 diff 内容
            pr_files: 变更文件列表
            full_file_context: 变更文件的完整内容（用于跨文件调用分析）
            inject_memory: 是否注入记忆库

        Returns:
            关联性发现列表
        """
        messages = self._build_impact_messages(
            pr_diff, pr_files, full_file_context, inject_memory
        )

        response = await self.llm.ainvoke(messages)

        try:
            findings = self._parse_findings(response.content)
            for f in findings:
                f["domain"] = "impact"
            return findings
        except Exception:
            return []

    def _build_impact_messages(
        self,
        pr_diff: str,
        pr_files: list[str],
        full_file_context: str,
        inject_memory: bool = True
    ):
        """构建 Impact Agent 的 LLM 消息"""
        files_str = "\n".join(f"- {f}" for f in pr_files)

        system_content = self.system_prompt

        if inject_memory:
            try:
                from src.tools.review_memory import recall_knowledge
                memory = recall_knowledge(pr_diff)
                if memory:
                    system_content += memory
            except Exception:
                pass

        ctx_section = ""
        if full_file_context:
            ctx_section = f"""

## 📄 变更文件的完整内容（用于分析跨文件调用关系）

{full_file_context}

---
**重要**: 请基于以上完整文件内容，分析变更方法调用了哪些**其他文件**的函数/方法，
以及哪些**其他文件**可能调用了这些变更方法。特别关注跨文件的委托调用和依赖关系。"""

        human_content = f"""## PR 变动文件
{files_str}

## PR Diff 内容
```diff
{pr_diff}
```
{ctx_section}

请审查以上代码变更的**关联性影响**，重点关注:
1. **跨文件调用**: 变更方法调用了哪些其他文件的函数？是否存在不必要的委托层？
2. **调用方兼容性**: 函数签名变更是否影响其他文件的调用方？
3. **命名冲突**: 新增符号是否与其他文件的已有符号重名？
4. **影响半径**: 变更方法被多少外部文件引用？
5. **隐式依赖**: 变更是否依赖了其他模块的全局状态或单例？

按 JSON 格式输出发现的问题。如果没有关联性问题，返回空的 findings 数组。"""

        return [
            SystemMessage(content=system_content),
            HumanMessage(content=human_content),
        ]

    def _parse_findings(self, content: str) -> list[dict]:
        """从 LLM 响应中解析 JSON 格式的 findings"""
        try:
            # 尝试直接解析
            data = json.loads(content)
            if isinstance(data, dict) and "findings" in data:
                return data["findings"]
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 块
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, dict) and "findings" in data:
                    return data["findings"]
                if isinstance(data, list):
                    return data
            except json.JSONDecodeError:
                pass

        return []
