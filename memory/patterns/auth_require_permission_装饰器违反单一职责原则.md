---
name: "auth_require_permission 装饰器违反单一职责原则"
description: "该装饰器同时承担了 JWT 解析、权限校验、审计日志记录和频率限制四种职责。这导致装饰器难以理解、测试和维护。任何职责的变化都需要修改同一个函数，违反了开闭原则。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:148-168
- **描述**: 该装饰器同时承担了 JWT 解析、权限校验、审计日志记录和频率限制四种职责。这导致装饰器难以理解、测试和维护。任何职责的变化都需要修改同一个函数，违反了开闭原则。
- **修复**: 拆分为多个独立的装饰器或中间件：1) @parse_jwt：负责解析和验证 JWT；2) @require_permission('admin')：负责权限校验；3) @audit_log：负责记录审计日志；4) @rate_limit：负责频率限制。每个装饰器只做一件事。

### 案例 2
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:178-210
- **描述**: 该装饰器同时承担了 4 种职责：JWT 解析、权限校验、审计日志记录、频率限制。这违反了单一职责原则（SRP），导致装饰器难以理解、测试和维护。任何职责的变化都需要修改同一个函数。
- **修复**: 将装饰器拆分为多个独立的装饰器，每个只负责一个职责：@jwt_required @require_permission('admin') @audit_log @rate_limit。这样每个装饰器都可以独立测试和复用。


### 案例 3
- **日期**: 2026-06-04 17202
- **来源 PR**: feat: 增加两个新方法
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:54-84
- **描述**: JwtUtil 类原本只负责 JWT 的生成和解析（generateToken/parseToken），现在新增了 getUserIdFromToken 和 isTokenValid 两个方法。虽然功能相关，但工具类正在逐渐演变为一个杂乱的“万能类”，包含了 token 解析、用户 ID 提取、有效性验证等多个职责。这违反了单一职责原则（SRP），随着时间推移，该类会变得越来越臃肿，难以维护和测试
- **修复**: 考虑将 JWT 相关操作拆分为更细粒度的服务类，例如创建 JwtTokenService 接口，包含 getUserId(token)、isValid(token) 等方法，并在实现类中注入 JwtUtil 或直接使用 JJWT 库。这样既保持了职责清晰，又便于单元测试（可以 mock 服务接口）。

### 案例 4
- **日期**: 2026-06-04 17292
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:20-52
- **描述**: UserContext 类原本的职责是管理用户上下文（通过 ThreadLocal 存储当前用户信息），但本次 PR 新增了三个方法：getTokenRemainingTime、generateToken、parseToken，这些方法仅仅是 JwtUtil 对应方法的简单委托调用。这导致 UserContext 的职责从'管理用户上下文'扩展到了'JWT 工具方法的代理层'，违反了单一职责原则（
- **修复**: 移除 UserContext 中新增的三个委托方法（getTokenRemainingTime、generateToken、parseToken），让调用方直接使用 JwtUtil 的对应方法。如果确实需要为某些方法提供更友好的接口，应在 JwtUtil 中直接增强，而不是在另一个类中创建委托层。

### 案例 5
- **日期**: 2026-06-04 17381
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:15-46
- **描述**: UserContext 原本的职责是管理当前线程的用户上下文（通过 ThreadLocal 存储/移除用户信息）。本次 PR 为其新增了三个与 JWT 操作相关的静态方法（getTokenRemainingTime、generateToken、parseToken），这些方法仅仅是 JwtUtil 对应方法的直接委托。这导致 UserContext 的职责从'用户上下文管理'扩展到了'JWT 工具
- **修复**: 删除 UserContext 中新增的三个委托方法，让调用方直接使用 JwtUtil 的静态方法。如果确实需要为 JwtUtil 的方法提供更友好的命名或默认参数，应该在 JwtUtil 内部添加重载方法，而不是在另一个不相关的类中创建委托。

### 案例 6
- **日期**: 2026-06-04 17381
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:15-50
- **描述**: UserContext 类原本的职责是管理当前线程的用户上下文（通过 ThreadLocal 存储和移除用户信息）。本次 PR 新增了三个方法：getTokenRemainingTime、generateToken、parseToken，这些方法仅仅是 JwtUtil 对应方法的简单委托调用。将 JWT 工具方法添加到 UserContext 类中，导致该类职责不清晰，既负责线程上下文管理，又负责
- **修复**: 建议将这些 JWT 相关的委托方法直接放在调用方代码中，或者保持 JwtUtil 作为唯一的 JWT 工具类入口。如果确实需要在 UserContext 中提供便捷方法，请考虑将类重命名为更通用的名称（如 UserUtils），或者将 JWT 相关方法提取到独立的 Service 类中。

### 案例 7
- **日期**: 2026-06-04 17384
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:18-50
- **描述**: UserContext 原本的职责是管理当前线程的用户上下文（通过 ThreadLocal 存储和清除用户信息）。本次 PR 新增了三个方法（getTokenRemainingTime、generateToken、parseToken），这些方法仅仅是直接委托给 JwtUtil 的对应方法，没有增加任何业务逻辑或上下文相关的处理。这导致 UserContext 的职责从'管理用户上下文'膨胀为'J
- **修复**: 删除 UserContext 中这三个纯委托方法。调用方应直接使用 JwtUtil 的静态方法。如果确实需要一个统一的 Token 操作入口，应该创建一个专门的 TokenService 或 TokenUtil 类，而不是将职责混杂在 UserContext 中。

### 案例 8
- **日期**: 2026-06-04 17455
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:22-40
- **描述**: UserContext 原本是一个专注于 ThreadLocal 用户上下文管理的工具类（setUser/getUser/removeUser），现在新增了三个与 JWT 操作相关的方法（getTokenRemainingTime、generateToken、parseToken），这些方法完全委托给 JwtUtil。这导致 UserContext 的职责变得模糊，违反了单一职责原则。
- **修复**: 将新增的三个 JWT 相关方法从 UserContext 中移除，让调用方直接使用 JwtUtil 中的方法。如果确实需要封装，可以考虑创建一个新的 Facade 类或直接在 JwtUtil 中提供这些方法。
