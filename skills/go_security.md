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
