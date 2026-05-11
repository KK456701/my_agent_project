# Go 架构审查技能

## 常见架构问题

### 包循环依赖
- **特征**: package A import B, package B import A
- **修复**: 抽取公共接口/接口层，依赖反转
- **严重程度**: high

### 接口滥用
- **特征**: 定义大接口（>5 个方法），违反接口隔离原则
- **修复**: 拆分为小接口，按需组合

### 错误处理忽略
- **特征**: `_ = someFunc()` / 忽略 error 返回值
- **修复**: 检查 error，至少 log 记录

### 全局状态
- **特征**: 包级 `var` 可变状态，测试困难
- **修复**: 依赖注入，struct 封装状态

### 过度使用 interface{}
- **特征**: `func(data interface{})` 丢失类型安全
- **修复**: 泛型（Go 1.18+）或具体类型

---

## ⚡ 确定性匹配规则（Skills Cache）

```yaml
rules:
  - pattern: '_\s*=\s*\w+\(.*\)\s*$'
    severity: medium
    title: "忽略函数返回的 error — 应用 _ 吞掉了错误"
    fix: "检查 error 返回值: err := someFunc(); if err != nil { return err }"

  - pattern: 'interface\s*\{\}'
    severity: medium
    title: "使用 interface{} 丢失类型安全"
    fix: "考虑使用泛型（Go 1.18+）或定义具体接口类型"
```
