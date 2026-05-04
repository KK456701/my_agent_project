"""
Agent 基类 — 所有审查 Agent 的公共抽象
"""
from abc import ABC, abstractmethod
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from config import config


class BaseReviewAgent(ABC):
    """审查 Agent 基类"""

    domain: str                       # security / performance / architecture
    prompt_file: str                  # prompts/xxx.md

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or config.MODEL_NAME
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=config.MODEL_TEMPERATURE,
            api_key=config.API_KEY,
            base_url=config.API_BASE or None,
        )
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        """加载 prompts 目录下的 system prompt"""
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / self.prompt_file
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt 文件未找到: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    @abstractmethod
    async def review(self, pr_diff: str, pr_files: list[str]) -> list[dict]:
        """
        审查 PR diff，返回发现的问题列表
        
        返回格式：[{"file":..., "lines":..., "severity":..., "title":..., ...}, ...]
        """
        ...

    def _build_messages(self, pr_diff: str, pr_files: list[str], inject_memory: bool = True):
        """构建 LLM 消息（可选注入记忆库知识）"""
        files_str = "\n".join(f"- {f}" for f in pr_files)

        system_content = self.system_prompt

        # 🧠 注入记忆库中的已知模式
        if inject_memory:
            from src.tools.review_memory import recall_knowledge
            memory = recall_knowledge(pr_diff)
            if memory:
                system_content += memory

        return [
            SystemMessage(content=system_content),
            HumanMessage(content=f"""## PR 变动文件
{files_str}

## PR Diff 内容
```diff
{pr_diff}
```

请仔细审查以上代码变更，按照 JSON 格式输出你发现的所有问题。
如果代码没有问题，返回空的 findings 数组。"""),
        ]
