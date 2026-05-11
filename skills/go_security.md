# Go 安全审查技能

## 常见漏洞清单

### SQL 注入
- **特征**: `fmt.Sprintf("SELECT ... WHERE name = '%s'", name)` / 字符串拼接 SQL
- **检测**: `db.Query(fmt.Sprintf(...))`, `db.Exec("..." + userInput)`
- **修复**: 占位符 `db.Query("SELECT ... WHERE name = $1", name)`
- **严重程度**: critical

### 硬编码密钥
- **特征**: `var secretKey = "xxx"` / `const apiKey = "xxx"`
- **修复**: `os.Getenv("SECRET_KEY")` 或密钥管理服务
- **严重程度**: high

### Goroutine 泄漏
- **特征**: 启动 goroutine 但没有 context 取消或 channel 关闭机制
- **修复**: 用 `context.WithCancel` + `defer cancel()`，或用 `sync.WaitGroup`
- **严重程度**: high

### 竞态条件
- **特征**: 多 goroutine 读写同一变量无锁保护
- **修复**: `sync.Mutex` / `sync.RWMutex` / `channel`
- **严重程度**: high

### 路径遍历
- **特征**: `os.Open(userInput)` / `ioutil.ReadFile(userInput)` 未校验
- **修复**: `filepath.Clean()` + 白名单校验
- **严重程度**: high

### 不安全随机数
- **特征**: `math/rand` 用于安全场景（token 生成、密码重置）
- **修复**: `crypto/rand`
- **严重程度**: medium

---

## ⚡ 确定性匹配规则（Skills Cache）

```yaml
rules:
  - pattern: 'fmt\.Sprintf\(".*SELECT.*FROM.*WHERE'
    severity: critical
    title: "SQL 注入 — 使用 fmt.Sprintf 拼接 SQL"
    fix: "使用占位符: db.Query('SELECT ... WHERE name = $1', name)"

  - pattern: 'db\.Query\(fmt\.Sprintf'
    severity: critical
    title: "SQL 注入 — 使用 fmt.Sprintf 构建 SQL"
    fix: "使用占位符: db.Query('SELECT ... WHERE name = $1', name)"

  - pattern: 'var\s+\w*[Ss]ecret\w*\s*=\s*"'
    severity: high
    title: "硬编码密钥"
    fix: "改为 os.Getenv('SECRET_KEY') 从环境变量读取"

  - pattern: 'math/rand'
    severity: medium
    title: "不安全的随机数 — math/rand 用于安全场景"
    fix: "改用 crypto/rand"

  - pattern: 'go\s+func\(.*\)\s*\{'
    severity: medium
    title: "Goroutine 启动 — 检查是否有 context 取消机制"
    fix: "确保 goroutine 有 context.WithCancel 或 channel 退出机制"
```
