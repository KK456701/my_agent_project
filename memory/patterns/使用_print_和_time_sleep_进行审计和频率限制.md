# 模式: 使用 print 和 time.sleep 进行审计和频率限制

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 logging.getLogger(__name__).info() 替代 print()。使用异步限流器或令牌桶算法替代 time.sleep()，避免阻塞主线程。

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:209-210
- **严重程度**: medium
- **描述**: 装饰器中使用 print() 进行审计日志记录，应使用 logging 模块。使用 time.sleep(0.01) 模拟频率限制会阻塞线程，影响性能。
- **建议**: 使用 logging.getLogger(__name__).info() 替代 print()。使用异步限流器或令牌桶算法替代 time.sleep()，避免阻塞主线程。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
