"""
State 定义 — 辩论式多智能体代码审查的核心状态机

状态流转：
    PR 输入 → 分级路由 → 各 Agent 独立审查 → 碰撞检测 → 辩论循环 → 生成报告
"""
from typing import TypedDict, Annotated, List, Optional, Literal
from dataclasses import dataclass, field
from enum import Enum
import operator


# ============================================================
# 基础数据结构
# ============================================================

class Severity(str, Enum):
    """问题严重程度"""
    CRITICAL = "critical"    # 必须修复，有安全/崩溃风险
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"            # 建议性意见


class ReviewDomain(str, Enum):
    """审查领域"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"


class DebateStatus(str, Enum):
    """辩论状态"""
    CONSENSUS = "consensus"          # 已达成共识
    STALEMATE = "stalemate"           # 僵局，需人工裁决
    ESCALATED = "escalated"          # 已升级给人类
    PENDING = "pending"              # 待辩论


@dataclass
class CodeIssue:
    """单个代码问题"""
    file_path: str
    line_start: int
    line_end: int
    severity: Severity
    domain: ReviewDomain
    title: str                     # 简短描述
    description: str               # 详细说明
    suggestion: str                # 修复建议
    code_snippet: str = ""         # 问题代码片段


@dataclass
class Conflict:
    """
    冲突：两个 Agent 对同一段代码有不同判断
    
    例如：
    - Security 认为第 42 行是 SQL 注入（高危）
    - Performance 认为修复方案会导致性能下降
    → 需要辩论
    """
    conflict_id: str
    file_path: str
    line_range: tuple[int, int]
    positions: dict[ReviewDomain, str] = field(default_factory=dict)
    # positions 示例: {"security": "SQL 注入，必须参数化", "performance": "参数化有 10% 开销"}
    debate_rounds: int = 0
    status: DebateStatus = DebateStatus.PENDING
    resolution: str = ""           # 最终决议


@dataclass
class ReviewReport:
    """最终审查报告"""
    summary: str                   # 总评
    issues: List[CodeIssue] = field(default_factory=list)
    conflicts_resolved: List[Conflict] = field(default_factory=list)
    conflicts_escalated: List[Conflict] = field(default_factory=list)
    total_tokens: int = 0
    debate_rounds: int = 0


# ============================================================
# LangGraph State — 贯穿整个图的共享状态
# ============================================================

class DebateState(TypedDict):
    """
    LangGraph 全局状态
    
    每个节点读取 / 写入这个 TypedDict，LangGraph 自动管理状态流转。
    """

    # --- 输入 ---
    pr_title: str                              # PR 标题
    pr_diff: str                               # PR 的 git diff 内容
    pr_files: List[str]                        # 变动的文件列表
    commit_message: str                        # commit 信息（用于智能路由）

    # --- 路由 ---
    review_mode: str                           # "fast" | "dual" | "full"
    route_reason: str                          # 路由决策理由（用于日志/面试展示）
    active_domains: List[str]                  # 需要参与审查的领域

    # --- 各 Agent 审查结果（Reducer: 追加合并） ---
    security_findings: Annotated[List[dict], operator.add]
    performance_findings: Annotated[List[dict], operator.add]
    architecture_findings: Annotated[List[dict], operator.add]

    # --- 辩论阶段 ---
    conflicts: List[dict]                      # 当前待解决的冲突列表
    debate_round: int                          # 当前辩论轮次
    debate_history: Annotated[List[dict], operator.add]  # 辩论历史

    # --- 输出 ---
    final_report: str                          # Markdown 格式的最终报告
    escalated: bool                            # 是否有升级给人类的问题

    # --- 元数据 ---
    total_tokens: int                          # Token 消耗统计
    error: str                                 # 错误信息
