"""
智能路由模块 — 生产级 PR 分级策略

不再只数行数，而是综合三个维度：
1. 关键文件识别（auth.py / payment.py → 强制全量审查）
2. 文件类型感知（配置文件可降级，核心逻辑升级）
3. Commit 语义分析（hotfix → 快审，refactor → 全量）

面试可讲：从简单行数启发式 → 多维智能路由的演进过程
"""
from typing import List, Tuple
from enum import Enum


class RouteMode(str, Enum):
    FAST = "fast"      # 1 Agent, security only
    DUAL = "dual"      # 2 Agent, security + performance
    FULL = "full"      # 3 Agent, 全阵容


# ============================================================
# 维度 1：关键文件 — 碰了就强制 full
# ============================================================

CRITICAL_FILE_PATTERNS = [
    # 认证 & 权限
    "auth", "authenticate", "authorize", "permission", "rbac", "acl",
    "login", "session", "token", "jwt", "oauth", "sso", "ldap",
    # 加密 & 安全
    "crypto", "encrypt", "decrypt", "cipher", "hash", "signature",
    "security", "sanitize", "validator",
    # 支付 & 敏感数据
    "payment", "billing", "invoice", "transaction", "wallet",
    "credit_card", "pii", "gdpr",
    # 核心业务入口
    "middleware", "interceptor", "filter_chain", "pipeline",
]


def is_critical_file(filepath: str) -> bool:
    """
    判断文件是否为关键文件（触及强制 full 审查）
    
    规则：
    - 文件名包含 auth/security/payment/crypto 等关键词
    - 匹配时忽略大小写和路径
    
    示例：
        src/auth/login.py → True
        src/utils/helper.py → False
        app/middleware/auth_middleware.go → True
    """
    filename_lower = filepath.lower()
    for pattern in CRITICAL_FILE_PATTERNS:
        if pattern in filename_lower:
            return True
    return False


# ============================================================
# 维度 2：文件类型 — 配置文件 vs 核心代码
# ============================================================

CONFIG_EXTENSIONS = {".yml", ".yaml", ".json", ".toml", ".env", ".ini", ".cfg", ".properties", ".xml"}
INFRA_PATTERNS = {"dockerfile", "docker-compose", "makefile", ".tf", ".sh", ".ps1"}
DOC_PATTERNS = {".md", ".rst", ".txt", ".adoc"}

# 核心代码扩展名（改这些文件的审查收益最高）
CORE_CODE_EXTENSIONS = {".py", ".java", ".go", ".ts", ".tsx", ".rs", ".cpp", ".c", ".h", ".js", ".jsx", ".rb", ".php", ".swift", ".kt"}


def classify_file(filepath: str) -> str:
    """
    将文件分为三类：config / infra_doc / core_code
    
    Returns:
        "config" | "infra_doc" | "core_code"
    """
    fp = filepath.lower()

    # 特殊文件名
    for pattern in INFRA_PATTERNS:
        if pattern in fp:
            return "infra_doc"

    # 扩展名
    for ext in CONFIG_EXTENSIONS:
        if fp.endswith(ext):
            return "config"

    for ext in DOC_PATTERNS:
        if fp.endswith(ext):
            return "infra_doc"

    return "core_code"


def analyze_file_composition(files: List[str]) -> Tuple[int, int, int]:
    """
    分析文件组成：核心代码 / 配置 / 基础设施&文档
    
    Returns:
        (core_count, config_count, infra_doc_count)
    """
    core = config_count = infra_doc = 0
    for f in files:
        t = classify_file(f)
        if t == "core_code":
            core += 1
        elif t == "config":
            config_count += 1
        else:
            infra_doc += 1
    return core, config_count, infra_doc


# ============================================================
# 维度 3：Commit 语义 — 看 commit message 判断意图
# ============================================================

HOTFIX_KEYWORDS = ["hotfix", "urgent", "emergency", "critical", "incident", "outage", "patch"]
REFACTOR_KEYWORDS = ["refactor", "migration", "rewrite", "overhaul", "redesign", "restructure"]
FEATURE_KEYWORDS = ["feat", "feature", "add ", "implement", "introduce"]


def analyze_commit_intent(message: str) -> str:
    """
    从 commit message 推断变更意图
    
    Returns:
        "hotfix" | "refactor" | "feature" | "unknown"
    """
    msg = message.lower()

    for kw in HOTFIX_KEYWORDS:
        if kw in msg:
            return "hotfix"

    for kw in REFACTOR_KEYWORDS:
        if kw in msg:
            return "refactor"

    for kw in FEATURE_KEYWORDS:
        if kw in msg:
            return "feature"

    return "unknown"


# ============================================================
# 综合路由决策
# ============================================================

def smart_route(
    changed_lines: int,
    changed_files: int,
    files: List[str],
    commit_message: str = "",
    fast_track_max_lines: int = 30,
) -> Tuple[RouteMode, str]:
    """
    综合三维度的智能路由决策
    
    Args:
        changed_lines: 总变动行数
        changed_files: 变动文件数
        files: 变动文件路径列表
        commit_message: commit 信息（可选）
        fast_track_max_lines: 快速通道行数阈值
    
    Returns:
        (RouteMode, 决策理由) — 理由用于面试展示和日志
    """
    reasons = []

    # ── 维度 1：关键文件检查 ──
    has_critical = any(is_critical_file(f) for f in files)
    if has_critical:
        critical_files = [f for f in files if is_critical_file(f)]
        reasons.append(f"🔑 关键文件: {', '.join(critical_files[:3])}")

    # ── 维度 2：文件组成分析 ──
    core, cfg, infra = analyze_file_composition(files)
    if core > 0 or cfg > 0 or infra > 0:
        parts = []
        if core: parts.append(f"{core} 个核心代码")
        if cfg: parts.append(f"{cfg} 个配置")
        if infra: parts.append(f"{infra} 个基础设施")
        reasons.append(f"📂 文件组成: {', '.join(parts)}")

    # ── 维度 3：Commit 语义 ──
    if commit_message:
        intent = analyze_commit_intent(commit_message)
        intent_map = {"hotfix": "🚨 紧急修复", "refactor": "🔧 重构", "feature": "✨ 新功能", "unknown": ""}
        if intent_map.get(intent):
            reasons.append(f"💬 意图: {intent_map[intent]}")

    # ── 路由决策 ──
    base_reason = f"变动 {changed_lines} 行 / {changed_files} 个文件"

    # 规则 A：关键文件 → 强制 full
    if has_critical:
        return RouteMode.FULL, f"{base_reason} + 关键文件强制全量审查"

    # 规则 B：全是配置/文档改动 → 降级
    if core == 0 and changed_files > 0:
        # 纯配置/文档改动 → 快速通道
        reasons.append("纯配置/文档变更 → 降级")
        return RouteMode.FAST, f"{base_reason} + 纯配置/文档变更"

    # 规则 C：Commit 语义覆盖
    if commit_message:
        intent = analyze_commit_intent(commit_message)
        if intent == "hotfix" and not has_critical:
            return RouteMode.DUAL, f"{base_reason} + hotfix 加速审查（跳过架构）"
        if intent == "refactor":
            return RouteMode.FULL, f"{base_reason} + refactor 触发全量审查"

    # 规则 D：文件数 + 行数 综合判断（兜底）
    if changed_files > 5 or changed_lines >= 200:
        return RouteMode.FULL, f"{base_reason} → 深度模式"
    elif changed_lines < fast_track_max_lines and changed_files <= 2:
        return RouteMode.FAST, f"{base_reason} → 快速通道"
    else:
        return RouteMode.DUAL, f"{base_reason} → 标准模式"
