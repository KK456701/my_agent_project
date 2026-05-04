"""
辩论式多智能体代码审查系统 — 配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env（override=True 强制覆盖已存在的环境变量，防止旧值残留）
load_dotenv(Path(__file__).parent / ".env", override=True)


class Config:
    """全局配置"""

    # --- LLM ---
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o")
    MODEL_TEMPERATURE: float = float(os.getenv("MODEL_TEMPERATURE", "0.2"))
    API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    API_BASE: str = os.getenv("OPENAI_API_BASE", "")

    # 轻量模型（用于分级路由中的快速通道）
    LITE_MODEL_NAME: str = os.getenv("LITE_MODEL_NAME", "gpt-4o-mini")

    # --- 辩论参数 ---
    MAX_DEBATE_ROUNDS: int = int(os.getenv("MAX_DEBATE_ROUNDS", "3"))
    CONSENSUS_THRESHOLD: float = float(os.getenv("CONSENSUS_THRESHOLD", "0.8"))

    # --- PR 分级路由 ---
    # 小于此行数的 PR 走快速通道（单 Agent）
    FAST_TRACK_MAX_LINES: int = int(os.getenv("FAST_TRACK_MAX_LINES", "50"))

    # --- 输出 ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> bool:
        """验证必要配置"""
        if not cls.API_KEY:
            raise ValueError("请在 .env 中设置 OPENAI_API_KEY")
        return True


config = Config()
