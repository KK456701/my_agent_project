# JavaScript/TypeScript 性能审查技能

## 常见性能反模式

### 不必要的重渲染（React）
- **特征**: 组件未用 `React.memo` / `useMemo` / `useCallback`
- **修复**: 合理使用 memo 系列 API
- **影响**: 大量不必要的 VDOM diff

### 内存泄漏
- **特征**: `useEffect` 未清理 `addEventListener` / `setInterval` / `subscription`
- **修复**: `useEffect` 返回 cleanup 函数
- **影响**: SPA 长时间使用后卡顿

### 大列表渲染
- **特征**: 直接 `.map()` 渲染 1000+ 条数据
- **修复**: 虚拟列表 (react-window / react-virtuoso)
- **影响**: 首次渲染阻塞

### 过度数据获取
- **特征**: `useEffect` 内 fetch 无依赖导致无限循环
- **修复**: 正确设置依赖数组
- **影响**: API 请求风暴

### 未代码分割
- **特征**: 所有组件打包在一个 bundle
- **修复**: `React.lazy()` + `Suspense` 动态导入

---

## ⚡ 确定性匹配规则（Skills Cache）

```yaml
rules:
  - pattern: 'useEffect\(\(\)\s*=>\s*\{[^}]*addEventListener'
    severity: medium
    title: "内存泄漏风险 — useEffect 内 addEventListener 无 cleanup"
    fix: "在 useEffect 返回清理函数中调用 removeEventListener"

  - pattern: '\.map\(.*\)\.slice\(0,\s*\d+\)'
    severity: medium
    title: "大列表渲染 — 先 map 再 slice 浪费计算"
    fix: "先 slice 再 map 减少不必要的遍历"
```
