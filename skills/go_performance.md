# Go 性能审查技能

## 常见性能反模式

### Goroutine 泄漏
- **特征**: goroutine 启动后无法正常退出，没有 context 取消
- **修复**: `context.WithCancel` + `defer cancel()`，channel close 信号
- **影响**: 内存持续增长、CPU 浪费

### 不必要的内存分配
- **特征**: 循环内 `make([]T, 0)` / `new(T)` / 频繁字符串拼接
- **修复**: 预分配容量 `make([]T, 0, expected)`，用 `strings.Builder`
- **影响**: GC 压力增大

### 未复用 HTTP 连接
- **特征**: 每次请求 `http.Get()` 或新建 `http.Client`
- **修复**: 全局 `http.Client` 复用，设置 `MaxIdleConns`
- **影响**: 连接池耗尽、TLS 握手开销

### 锁粒度过大
- **特征**: 锁内包含 I/O 操作或耗时计算
- **修复**: 缩小锁范围，用 `sync.RWMutex`，读写分离
- **影响**: 并发吞吐下降

### Channel 阻塞
- **特征**: 无缓冲 channel 发送端无接收者，阻塞 goroutine
- **修复**: 设缓冲大小，或用 `select` + `default` 非阻塞发送
- **影响**: goroutine 堆积、死锁

---

## ⚡ 确定性匹配规则（Skills Cache）

```yaml
rules:
  - pattern: 'for\s+.*range.*\{\s*\n\s*.*=.*make\(\[\]'
    severity: medium
    title: "循环内重复分配 slice — 应预分配容量"
    fix: "在循环外预分配: make([]T, 0, expectedSize)"

  - pattern: 'db\.Query\(.*\)\s*\n\s*defer rows\.Close\(\)'
    severity: low
    title: "defer rows.Close() 位置不当 — 应在 err 检查后"
    fix: "先检查 err != nil，再 defer rows.Close()"
```
