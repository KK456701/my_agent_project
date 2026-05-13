"""
语义精排模块 — RAG Rerank 思路的落地

模型：从 ModelScope 下载中文 Embedding（国内可访问，无需 HuggingFace）
默认: damo/nlp_corom_sentence-embedding_chinese-base
- 110M 参数，~420MB 磁盘，256 维向量，CPU < 10ms/对

⚠️ 优雅降级: 模型下载失败或未安装依赖时自动跳过
"""
from pathlib import Path
from typing import Optional
import numpy as np

_MODEL = None
_MODEL_NAME = "damo/nlp_corom_sentence-embedding_chinese-base"
_LOCAL_DIR = Path(__file__).parent.parent.parent / ".model_cache"


def _get_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    try:
        from modelscope import snapshot_download
        from sentence_transformers import SentenceTransformer
        _LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        model_path = snapshot_download(_MODEL_NAME, cache_dir=str(_LOCAL_DIR))
        _MODEL = SentenceTransformer(model_path)
        return _MODEL
    except ImportError:
        return None
    except Exception:
        return None


def compute_similarity(text_a: str, text_b: str) -> Optional[float]:
    model = _get_model()
    if model is None or not text_a or not text_b:
        return None
    try:
        emb_a = model.encode(text_a, convert_to_numpy=True)
        emb_b = model.encode(text_b, convert_to_numpy=True)
        return float(np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b)))
    except Exception:
        return None


def are_suggestions_contradictory(fix_a: str, fix_b: str) -> Optional[bool]:
    sim = compute_similarity(fix_a, fix_b)
    if sim is None:
        return None
    if sim > 0.7:
        return False
    if sim < 0.3:
        return True
    return None
