"""
冲突检测 + 辩论管线端到端测试

绕过 LLM Agent，直接用预制的矛盾 findings 验证 detect_conflicts → Consensus 整条链路。
"""
import asyncio
from src.tools.code_analyzer import detect_conflicts
from src.agents.consensus_agent import ConsensusAgent


# ── 预制的矛盾 findings ──
# 场景: JWT 缓存 — Security 要删, Performance 要留
FINDINGS = {
    "security": [
        {
            "file": "test.py",
            "lines": "20-33",
            "severity": "high",
            "title": "JWT 缓存永不过期导致 Token 泄漏",
            "description": "auth_require_permission 装饰器中 _TOKEN_CACHE 缓存 JWT 解析结果且永不过期。Token 被吊销后缓存仍有效，攻击者获取 Token 后可永久使用。",
            "suggestion": "删除 _TOKEN_CACHE，每次请求都调用 jwt.decode() 验证签名和过期时间。不要缓存 Token，缓存是安全隐患。"
        },
        {
            "file": "test.py",
            "lines": "47-52",
            "severity": "critical",
            "title": "使用 SHA256 进行密码哈希",
            "description": "verify_password_high_qps 使用 SHA256 + 固定 salt 进行密码验证。SHA256 作为密码哈希速度太快，GPU 每秒可试数十亿次，无法抵御暴力破解。",
            "suggestion": "将 SHA256 替换为 bcrypt(work_factor=12)。bcrypt 单次 200ms，但 GPU 暴力破解速度从 10 亿次/秒降到几千次/秒。安全性是硬性要求，不可妥协。"
        },
        {
            "file": "test.py",
            "lines": "68-70",
            "severity": "critical",
            "title": "f-string 拼接 SQL 导致注入",
            "description": "search_orders 中 keyword 通过 f-string 拼接到 SQL LIKE 子句。攻击者可构造 keyword='' OR 1=1 -- 绕过查询逻辑，泄露所有订单数据。",
            "suggestion": "必须使用参数化查询: cursor.execute('SELECT * FROM orders WHERE title LIKE ?', (f'%{keyword}%',))。参数化是防止 SQL 注入的唯一正确方式，不可妥协。"
        },
    ],
    "performance": [
        {
            "file": "test.py",
            "lines": "20-33",
            "severity": "high",
            "title": "每次 jwt.decode() 导致性能瓶颈",
            "description": "auth_require_permission 装饰器在 5000 QPS 下每次调用 jwt.decode() 耗时 50ms，导致总延迟不可接受。必须使用缓存来降低延迟。",
            "suggestion": "保留 _TOKEN_CACHE，添加 TTL(5分钟) 和 LRU 淘汰策略(maxsize=1000)。缓存 key 使用 Token 完整 SHA256 哈希。直接删除缓存会导致 QPS 从 5000 降到 20，系统不可用。"
        },
        {
            "file": "test.py",
            "lines": "47-52",
            "severity": "high",
            "title": "bcrypt 导致登录接口 P99 超标",
            "description": "当前峰值 5000 QPS，bcrypt(work_factor=12) 单次 200ms。如果用 bcrypt，需要 1000 个 CPU 核心才能维持 QPS，成本不可接受。",
            "suggestion": "继续使用 SHA256，但改为 SHA256 + 每用户随机 salt + 100000 次 PBKDF2 迭代。这样 GPU 暴力破解速度约 1000 次/秒，足够安全，且单次验证只需 2ms，远优于 bcrypt 的 200ms。"
        },
        {
            "file": "test.py",
            "lines": "68-70",
            "severity": "high",
            "title": "参数化导致 LIKE 索引失效",
            "description": "search_orders 中 title 列有全文索引。参数化查询会导致 SQLite 优化器选择全表扫描而非索引查找，QPS 从 3000 降到 50。这是已知的 SQLite 限制。",
            "suggestion": "保持 f-string 拼接，但使用白名单过滤 keyword（只允许字母数字和空格），并在拼接前用 shlex.quote() 转义。参数化在此场景会导致索引失效，不可接受。"
        },
    ],
}


async def main():
    print("=" * 60)
    print("🔴 冲突检测测试（预制矛盾 findings）")
    print("=" * 60)

    # ── Step 1: 冲突检测 ──
    adversarial = detect_conflicts(FINDINGS)
    orth = detect_conflicts._last_orthogonal

    print(f"\n📊 检测结果:")
    print(f"   输入: {sum(len(v) for v in FINDINGS.values())} 个 findings")
    print(f"   对抗性冲突: {len(adversarial)}")
    print(f"   正交发现:   {len(orth)}")

    if not adversarial:
        print("\n❌ 没有检测到对抗性冲突！")
        print("   预期: 3 对 (缓存 / 密码哈希 / SQL参数化)")
        return

    print(f"\n🔴 对抗性冲突详情:")
    for c in adversarial:
        print(f"   {c['domain_a']} vs {c['domain_b']} — {c['file']} ({c['lines']})")
        print(f"   adversarial={c['adversarial']}")
        print()

    # ── Step 2: 辩论裁决 ──
    print("=" * 60)
    print("⚔️ Consensus 裁决")
    print("=" * 60)

    consensus = ConsensusAgent()
    for i, conflict in enumerate(adversarial):
        print(f"\n── 冲突 {i+1}: {conflict['domain_a']} vs {conflict['domain_b']} ──")
        print(f"   文件: {conflict['file']} ({conflict['lines']})")

        # 模拟最多 3 轮辩论
        history = []
        for round_num in range(1, 4):
            result = await consensus.resolve(conflict, history, round_num=round_num)
            resolution = result.get("resolution", "?")
            confidence = result.get("confidence", 0)

            print(f"   第 {round_num} 轮: resolution={resolution}, confidence={confidence:.2f}")

            history.append({
                "round": round_num,
                "conflict_id": conflict["conflict_id"],
                "status": "resolved" if resolution != "stalemate" else "pending",
                "resolution": resolution,
            })

            if resolution == "stalemate":
                if round_num >= 3:
                    print(f"   → 🔺 3 轮僵局，升级人工")
                    break
                print(f"   → 未达成共识，进入下一轮...")
            else:
                print(f"   → 裁决: {result.get('final_suggestion', '')[:200]}...")
                break

    print("\n" + "=" * 60)
    print("✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(main())
