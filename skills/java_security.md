# Java 安全审查技能

## 常见漏洞清单

### SQL 注入
- **特征**: 字符串拼接 SQL / `Statement` 直接拼接
- **检测**: `"SELECT * FROM users WHERE name = '" + name + "'"` / `String.format`
- **修复**: `PreparedStatement` 占位符 `?`
- **严重程度**: critical

### 硬编码密钥
- **特征**: `private static final String SECRET = "xxx"`
- **修复**: 环境变量 / `@Value` 注入 / Vault
- **严重程度**: high

### XXE (XML 外部实体注入)
- **特征**: `DocumentBuilderFactory` 未禁用外部实体
- **修复**: `setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)`
- **严重程度**: critical

### 反序列化漏洞
- **特征**: `ObjectInputStream.readObject()` 无校验
- **修复**: 白名单校验 / 使用 JSON 替代 Java 序列化
- **严重程度**: high

### 弱加密算法
- **特征**: `MessageDigest.getInstance("MD5")` / `"DES"`
- **修复**: `"SHA-256"` / `"AES/GCM/NoPadding"`
- **严重程度**: high


## ⚡ 确定性匹配规则（Skills Cache）

```yaml
rules:
  - pattern: 'MessageDigest\.getInstance\("MD5"\)'
    severity: high
    title: "不安全的 MD5 哈希"
    fix: "改为 MessageDigest.getInstance(\"SHA-256\")"

  - pattern: '\.execute\(\s*".*\+.*\+'
    severity: critical
    title: "SQL 注入 — 字符串拼接 SQL"
    fix: "使用 PreparedStatement: pstmt.setString(1, name)"

  - pattern: 'private\s+static\s+final\s+String\s+\w*[Ss]ecret\w*\s*=\s*"'
    severity: high
    title: "硬编码密钥"
    fix: "改为 @Value(\"${app.secret}\") 从配置文件读取"
```
