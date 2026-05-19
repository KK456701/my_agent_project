"""
辩论式多智能体代码审查系统 — 配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env（override=True 强制覆盖已存在的环境变量，防止旧值残留）
load_dotenv(Path(__file__).parent / ".env", override=True)

# 在导入其他库之前，显式设置 HuggingFace 镜像端点
_HF_ENDPOINT = os.getenv("HF_ENDPOINT", "")
if _HF_ENDPOINT:
    os.environ["HF_ENDPOINT"] = _HF_ENDPOINT

# 在导入其他库之前，显式设置代理（Python 不走浏览器代理）
for _proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    _proxy_val = os.getenv(_proxy_var, "")
    if _proxy_val:
        os.environ[_proxy_var] = _proxy_val
        os.environ[_proxy_var.upper()] = _proxy_val  # 兼容大小写


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

    # --- HuggingFace ---
    HF_ENDPOINT: str = os.getenv("HF_ENDPOINT", "https://huggingface.co")

    @classmethod
    def validate(cls) -> bool:
        """验证必要配置"""
        if not cls.API_KEY:
            raise ValueError("请在 .env 中设置 OPENAI_API_KEY")
        return True


config = Config()
