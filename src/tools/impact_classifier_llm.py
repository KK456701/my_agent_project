"""
DeepSeek 驱动的变更影响力分级器

替换正则版本 —— 让 LLM 判断哪些变更真正需要 CodeGraph 深挖

策略:
  1. 输入 PR diff → DeepSeek 分析每个变更行
  2. 输出三级分类: skip / light / deep
  3. deep 标记的变更自动触发 CodeGraph 调用方+源码查询
"""
import re
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from config import config

from src.tools.impact_classifier import (
    ChangeImpact, CG_PATH,
    _get_caller_count, _get_callers_detail,
    build_impact_report
)


@dataclass
class ClassifyResult:
    """DeepSeek 分类结果"""
    skip: list[ChangeImpact] = field(default_factory=list)
    light: list[ChangeImpact] = field(default_factory=list)
    deep: list[ChangeImpact] = field(default_factory=list)
    reasoning: str = ""  # DeepSeek 的推理过程


# ============================================================
# Prompt
# ============================================================

CLASSIFY_SYSTEM = """你是代码审查影响力分析专家。你的任务是分析 PR diff 中每个变更行，
判断它是否需要跨文件影响分析。

## 分类标准

### SKIP — 跳过（不需要任何分析）
- 注释变更 (//, /* */, #, <!-- -->)
- 日志/打印语句 (log.xxx, print, System.out, logger.)
- 纯格式/缩进/空白行
- 测试文件中的变更
- 字符串字面量微调（不改变逻辑）
- import 语句增删（除非删除的 import 影响编译）
- 包名/版本号变更

### LIGHT — 轻量分析（只需 CodeGraph 查调用方数量）
- 私有方法变更 (private)
- 局部变量重命名
- 函数体内逻辑微调（不改签名）
- 新增的私有辅助方法
- 代码风格/重构（功能等价）

### DEEP — 深度分析（需要 CodeGraph 完整源码+关系图）
- 公共方法签名变更 (public method 的参数/返回值/异常声明改变)
- 删除任何函数/方法（调用方会直接炸）
- 接口/抽象类/基类变更
- 数据模型字段变更 (@Entity, @Column, @Field)
- 配置常量/密钥变更 (SECRET_KEY, API_URL, TIMEOUT)
- 新增公共 API（可能命名冲突、破坏现有约定）

## 输出格式

严格按以下 JSON 输出，不要输出其他内容：

```json
{
  "reasoning": "一句话总结本次 PR 的整体影响评估",
  "decisions": [
    {
      "line": "+    public static Claims parseToken(String token) {",
      "file": "src/main/java/com/study/room/utils/JwtUtil.java",
      "level": "deep",
      "symbol": "parseToken",
      "reason": "新增公共方法，可能被多处调用"
    },
    {
      "line": "+    //asdasd5466556",
      "file": "src/main/java/com/study/room/utils/JwtUtil.java",
      "level": "skip",
      "symbol": "",
      "reason": "无意义注释"
    }
  ]
}
```

注意:
- 一行只对变更行（以 + 或 - 开头）做判断
- symbol 字段填实际代码符号名（函数名/类名/变量名），注释/格式等填空字符串
- level 只能是 "skip" / "light" / "deep"
"""


# ============================================================
# DeepSeek 分类器
# ============================================================

class DeepSeekClassifier:

    def __init__(self, model_name: str = None):
        self.llm = ChatOpenAI(
            model=model_name or config.MODEL_NAME,
            temperature=0,
            api_key=config.API_KEY,
            base_url=config.API_BASE or None,
        )

    def classify(
        self,
        diff_text: str,
        project_root: str,
        deep_threshold: int = 3
    ) -> ClassifyResult:
        """
        DeepSeek 分级 → CodeGraph 补充调用方数据

        流程:
          1. DeepSeek 分析 diff → 输出 skip/light/deep 分类
          2. 对 light 和 deep 标记的符号，CodeGraph 查调用方数量
          3. 调用方 ≥ threshold → 最终确认 deep
          4. 调用方 < threshold → 降级为 light
        """
        # ── 第 1 步：DeepSeek 分类 ──
        decisions = self._llm_classify(diff_text)
        if not decisions:
            return ClassifyResult(reasoning="LLM 分类失败")

        reasoning = decisions.get("reasoning", "")
        items = decisions.get("decisions", [])

        skip_list = []
        light_list = []
        deep_list = []

        for item in items:
            level = item.get("level", "skip")
            symbol = item.get("symbol", "")
            file_path = item.get("file", "")
            reason = item.get("reason", "")

            impact = ChangeImpact(
                symbol=symbol,
                kind="llm_classified",
                file=file_path,
                risk=level,
                reason=reason,
            )

            # ── 第 2 步：CodeGraph 验证 ──
            if level in ("light", "deep") and symbol:
                caller_count = _get_caller_count(symbol, project_root)
                impact.caller_count = caller_count

                if caller_count >= deep_threshold:
                    # 升级为深挖
                    impact.risk = "deep"
                    impact.reason += f" + CodeGraph 确认 {caller_count} 个调用方"
                    impact.callers = _get_callers_detail(symbol, project_root)
                    deep_list.append(impact)
                elif caller_count > 0:
                    impact.risk = "light"
                    impact.reason += f" (实际 {caller_count} 个调用方)"
                    light_list.append(impact)
                else:
                    impact.risk = "light"
                    impact.reason += " (无调用方)"
                    light_list.append(impact)
            elif level == "skip":
                skip_list.append(impact)
            elif level == "deep" and not symbol:
                # LLM 标记为 deep 但没给 symbol，降级
                impact.risk = "light"
                light_list.append(impact)

        return ClassifyResult(
            skip=skip_list,
            light=light_list,
            deep=deep_list,
            reasoning=reasoning,
        )

    def _llm_classify(self, diff_text: str) -> dict:
        """调用 DeepSeek 对 diff 分类"""
        # 截断过大的 diff（分类只需要变更行，不需要完整上下文）
        changed_lines = []
        for line in diff_text.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                changed_lines.append(line)
            elif line.startswith("-") and not line.startswith("---"):
                changed_lines.append(line)
        diff_compact = "\n".join(changed_lines[:200])  # 最多 200 行变更

        try:
            response = self.llm.invoke([
                SystemMessage(content=CLASSIFY_SYSTEM),
                HumanMessage(content=f"## PR 变更行\n\n```diff\n{diff_compact}\n```"),
            ])
            return self._parse_response(response.content)
        except Exception as e:
            print(f"[DeepSeekClassifier] LLM 调用失败: {e}")
            return {}

    def _parse_response(self, content: str) -> dict:
        """解析 DeepSeek 的 JSON 响应"""
        # 尝试直接解析
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # 提取 JSON 块
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 最后尝试：找 { 到 }
        brace_match = re.search(r'\{.*"decisions".*\}', content, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        print(f"[DeepSeekClassifier] 无法解析响应: {content[:200]}...")
        return {}


# ============================================================
# 便捷函数：替代原先的 classify_changes
# ============================================================

def classify_changes_llm(
    diff_text: str,
    project_root: str,
    deep_threshold: int = 3
) -> tuple[list, list, list]:
    """
    DeepSeek 驱动的变更分类（与 regex 版本接口一致）
    """
    classifier = DeepSeekClassifier()
    result = classifier.classify(diff_text, project_root, deep_threshold)
    return result.skip, result.light, result.deep
