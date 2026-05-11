# JavaScript/TypeScript 安全审查技能

## 常见漏洞清单

### XSS (跨站脚本)
- **特征**: `innerHTML = userInput` / `dangerouslySetInnerHTML`
- **修复**: `textContent` / DOMPurify 过滤
- **严重程度**: critical

### SQL/NoSQL 注入
- **特征**: 字符串拼接 SQL / `$where` 操作符直接使用用户输入（MongoDB）
- **修复**: 参数化查询 / ORM / Mongoose 校验
- **严重程度**: critical

### 敏感信息泄露
- **特征**: `console.log(token)` / `.env` 提交到前端 bundle
- **修复**: 移除 console.log / 环境变量用 `NEXT_PUBLIC_` 前缀管控
- **严重程度**: high

### 不安全的依赖
- **特征**: `eval(userInput)` / `new Function(userInput)`
- **修复**: 避免动态执行代码
- **严重程度**: critical

### CSRF
- **特征**: 状态变更接口无 CSRF Token
- **修复**: SameSite Cookie + CSRF Token

---

## ⚡ 确定性匹配规则（Skills Cache）

```yaml
rules:
  - pattern: '\.innerHTML\s*='
    severity: critical
    title: "XSS 风险 — 直接设置 innerHTML"
    fix: "改用 textContent 或 DOMPurify.sanitize()"

  - pattern: 'dangerouslySetInnerHTML'
    severity: critical
    title: "XSS 风险 — React dangerouslySetInnerHTML"
    fix: "改用 DOMPurify 过滤后再使用 dangerouslySetInnerHTML"

  - pattern: 'eval\(.*\)'
    severity: critical
    title: "代码注入 — 使用 eval()"
    fix: "避免使用 eval(), 改用 JSON.parse() 或安全解析器"

  - pattern: 'console\.log\(.*token'
    severity: high
    title: "敏感信息泄露 — console.log 输出 token"
    fix: "移除 console.log, 或使用日志脱敏"

  - pattern: '\.execute\(\s*`.*\$\{'
    severity: critical
    title: "SQL 注入 — 模板字符串拼接 SQL"
    fix: "使用参数化查询或 ORM 占位符"
```
