# TypeScript 最佳实践

## 常见问题

### 类型滥用 `any`
- **特征**: `const data: any = ...` / `(res: any) => ...`
- **修复**: 使用具体类型或 `unknown` + 类型守卫
- **严重程度**: medium

### 缺少空值检查
- **特征**: `user.name.toLowerCase()` 未检查 `user` 可能为 null
- **修复**: 可选链 `user?.name?.toLowerCase()` 或类型守卫

### 未使用严格模式
- **特征**: `tsconfig.json` 中 `strict: false`
- **修复**: 启用 `strict: true`

---

## ⚡ 确定性匹配规则（Skills Cache）

```yaml
rules:
  - pattern: ':\s*any\b'
    severity: medium
    title: "类型使用 any — 丢失类型安全"
    fix: "使用具体类型或 unknown + 类型守卫代替 any"
```
