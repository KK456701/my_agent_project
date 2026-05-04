"""
共识裁决 Agent — 分析冲突并给出有理有据的裁决
"""
import json
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from config import config


class ConsensusAgent:
    """共识裁决 Agent — 不继承 BaseReviewAgent（职责不同）"""

    domain = "consensus"

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or config.MODEL_NAME
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.1,  # 裁决需要确定性
            api_key=config.API_KEY,
            base_url=config.API_BASE or None,
        )
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "consensus.md"
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    async def resolve(self, conflict: dict, debate_history: list[dict] | None = None) -> dict:
        """
        裁决一个冲突
        
        Args:
            conflict: {
                "conflict_id": str,
                "file": str,
                "lines": str,
                "code_snippet": str,
                "positions": {domain: argument, ...},
            }
            debate_history: 之前的辩论记录
        
        Returns:
            {
                "resolution": "security|performance|architecture|compromise|stalemate",
                "reasoning": str,
                "final_suggestion": str,
                "confidence": float
            }
        """
        positions_text = "\n\n".join(
            f"**{domain} Agent**:\n{argument}"
            for domain, argument in conflict.get("positions", {}).items()
        )

        history_text = ""
        if debate_history:
            history_items = []
            for h in debate_history:
                if h.get("conflict_id") == conflict.get("conflict_id"):
                    history_items.append(
                        f"第 {h.get('round', '?')} 轮: {h.get('domain')} Agent 说: {h.get('argument', '')}"
                    )
            if history_items:
                history_text = "\n".join(history_items)

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""## 有争议的代码
文件: {conflict.get('file', '')}
行号: {conflict.get('lines', '')}
```python
{conflict.get('code_snippet', '')}
```

## 各方立场
{positions_text}

## 辩论历史
{history_text if history_text else '（第一轮辩论，无历史）'}

请给出你的裁决。"""),
        ]

        chain = self.llm | StrOutputParser()
        raw_response = await chain.ainvoke(messages)

        return self._parse_response(raw_response)

    @staticmethod
    def _parse_response(raw: str) -> dict:
        try:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]
                if raw.endswith("```"):
                    raw = raw[:-3].strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()

            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "resolution": "stalemate",
                "reasoning": "无法解析裁决结果",
                "final_suggestion": "请人工审查",
                "confidence": 0.0,
            }
