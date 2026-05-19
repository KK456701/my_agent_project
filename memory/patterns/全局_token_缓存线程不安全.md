# 模式: 全局 Token 缓存线程不安全

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用线程安全的缓存实现，如 threading.Lock 保护或使用 Redis。修改为：import threading; _TOKEN_CACHE_LOCK = threading.Lock(); with _TOKEN_CACHE_LOCK: ...

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:148-155
- **严重程度**: medium
- **描述**: _TOKEN_CACHE 是一个模块级字典，在多线程环境下同时读写会导致数据竞争（race condition），可能返回损坏的数据或导致程序崩溃。
- **建议**: 使用线程安全的缓存实现，如 threading.Lock 保护或使用 Redis。修改为：import threading; _TOKEN_CACHE_LOCK = threading.Lock(); with _TOKEN_CACHE_LOCK: ...

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
