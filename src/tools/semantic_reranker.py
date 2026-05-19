"""
语义精排模块

两个模型：
1. Embedding — 余弦相似度，用于 _check_same_issue（同一问题判断）
2. NLI — 矛盾检测，用于 _check_contradiction_v2 的规则后兜底

模型从 ModelScope 下载，均支持本地缓存和优雅降级。
"""
from pathlib import Path
from typing import Optional
import numpy as np

# ── Embedding 模型 ──
_EMB_MODEL = None
_EMB_MODEL_NAME = "damo/nlp_corom_sentence-embedding_chinese-base"

_LOCAL_DIR = Path(__file__).parent.parent.parent / ".model_cache"

# ── NLI 模型 ──
_NLI_MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"  # 多语言 NLI，支持中文
_NLI_MODEL = None
_NLI_TOKENIZER = None
_NLI_SKIPPED = False  # 永久跳过标记（模型下载失败或不可用）


def _get_nli_model():
    global _NLI_MODEL, _NLI_TOKENIZER, _NLI_SKIPPED
    if _NLI_MODEL is not None:
        return _NLI_MODEL, _NLI_TOKENIZER
    if _NLI_SKIPPED:
        return None, None
    _LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from transformers import DebertaV2ForSequenceClassification, AutoTokenizer
        local_model_dir = _LOCAL_DIR / _NLI_MODEL_NAME
        if local_model_dir.exists() and (local_model_dir / "pytorch_model.bin").exists():
            model_path = str(local_model_dir)
        else:
            model_path = _NLI_MODEL_NAME
        _NLI_TOKENIZER = AutoTokenizer.from_pretrained(model_path)
        _NLI_MODEL = DebertaV2ForSequenceClassification.from_pretrained(model_path)
        _NLI_MODEL.eval()
        return _NLI_MODEL, _NLI_TOKENIZER
    except Exception:
        _NLI_SKIPPED = True
        import sys
        print("[nli] NLI 模型不可用，已跳过（仅使用硬编码规则）", file=sys.stderr)
        return None, None


def _get_emb_model():
    global _EMB_MODEL
    if _EMB_MODEL is not None:
        return _EMB_MODEL
    try:
        from sentence_transformers import SentenceTransformer
        _LOCAL_DIR.mkdir(parents=True, exist_ok=True)
        local_model_dir = _LOCAL_DIR / _EMB_MODEL_NAME
        if local_model_dir.exists() and (local_model_dir / "pytorch_model.bin").exists():
            _EMB_MODEL = SentenceTransformer(str(local_model_dir))
            return _EMB_MODEL
        from modelscope import snapshot_download
        model_path = snapshot_download(_EMB_MODEL_NAME, cache_dir=str(_LOCAL_DIR))
        _EMB_MODEL = SentenceTransformer(model_path)
        return _EMB_MODEL
    except ImportError:
        return None
    except Exception:
        return None


def compute_similarity(text_a: str, text_b: str) -> Optional[float]:
    """两段文本的余弦相似度（Embedding 模型）"""
    model = _get_emb_model()
    if model is None or not text_a or not text_b:
        return None
    try:
        emb_a = model.encode(text_a, convert_to_numpy=True)
        emb_b = model.encode(text_b, convert_to_numpy=True)
        return float(np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b)))
    except Exception:
        return None


# ============================================================
# NLI 矛盾检测
# ============================================================

_NLI_LABEL_MAP = {"contradiction": 2, "entailment": 0, "neutral": 1}


def check_contradiction(fix_a: str, fix_b: str) -> Optional[bool]:
    """
    NLI 矛盾检测：fix_a 和 fix_b 是否逻辑矛盾？
    
    双向检测（A→B 和 B→A），任一方向判 contradiction 即认为矛盾。
    模型不可用时返回 None → 规则层接管，不影响系统。
    
    Returns:
        True  = 矛盾
        False = 非矛盾
        None  = 模型不可用
    """
    model, tokenizer = _get_nli_model()
    if model is None or not fix_a or not fix_b:
        return None

    import torch

    try:
        for premise, hypothesis in [(fix_a, fix_b), (fix_b, fix_a)]:
            inputs = tokenizer(
                premise[:256], hypothesis[:256],
                return_tensors="pt", truncation=True, max_length=512
            )
            with torch.no_grad():
                logits = model(**inputs).logits
                pred = torch.argmax(logits, dim=-1).item()

            if pred == _NLI_LABEL_MAP["contradiction"]:
                return True

        return False
    except Exception:
        return None
