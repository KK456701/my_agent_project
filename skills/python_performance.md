# Python 性能优化技能

## 常见性能反模式

### N+1 查询
- **特征**: 循环内执行数据库查询
- **检测**: `for` 循环内 `cursor.execute()` / `fetchone()` / `fetchall()`
- **修复**: 使用 `IN` 子句 / `JOIN` 批量查询
- **影响**: 1000 用户 = 1001 次查询 vs 2 次

### 不必要的列表构建
- **特征**: 先 `append` 到列表再遍历
- **修复**: 直接累加 / 生成器表达式
- **影响**: 省 O(n) 内存

### 数据库连接泄漏
- **特征**: `conn = connect()` 后无 `finally: conn.close()`
- **修复**: `with` 语句 / `try-finally`
- **影响**: 连接池耗尽

### 过度的对象创建
- **特征**: 循环内 `new Cipher()` / `new Client()`
- **修复**: 复用对象 / 对象池
- **影响**: CPU + 内存

### 同步阻塞
- **特征**: `time.sleep()` / 同步 I/O 在 async 上下文中
- **修复**: `asyncio.sleep()` / 异步 I/O
- **影响**: 阻塞事件循环

---

## ⚡ 确定性匹配规则（Skills Cache）

```yaml
rules:
  - pattern: 'for\s+\w+\s+in\s+\w+:\s*\n\s*cursor\.execute\('
    severity: critical
    title: "N+1 查询 — 循环内执行数据库查询"
    fix: "使用 SQL IN 子句一次查询: cursor.execute('SELECT ... WHERE id IN ({})'.format(','.join(['?']*len(ids))), ids)"

  - pattern: 'for\s+\w+\s+in\s+\w+:\s*\n\s*\w+\.execute\('
    severity: critical
    title: "N+1 查询 — 循环内执行数据库查询"
    fix: "使用批量查询替代逐条查询，将 N+1 次数据库往返降为 2 次"

  - pattern: '\.append\(.*\)\s*\n\s*for.*\.append'
    severity: medium
    title: "不必要的中间列表 — 可以先 append 再遍历"
    fix: "直接在循环中累加，省去中间列表的内存分配"
```
