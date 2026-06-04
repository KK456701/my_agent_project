---
name: "重复的 JWT 解析方法"
description: "新增的 parseToken 方法与下方已有的 parseToken 方法功能完全重复，导致代码冗余。虽然不会直接引发安全漏洞，但冗余代码增加了维护成本和潜在的逻辑不一致风险。"
---

## 历史案例

### 案例 1
- **日期**: 2026-06-04_134037
- **来源 PR**: feat: 增加从token获取userId的便捷方法22222245a
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java:32-42
- **描述**: 新增的 parseToken 方法与下方已有的 parseToken 方法功能完全重复，导致代码冗余。虽然不会直接引发安全漏洞，但冗余代码增加了维护成本和潜在的逻辑不一致风险。
- **修复**: 删除新增的重复方法，保留原有的 parseToken 方法。


### 案例 2
- **日期**: 2026-06-04 15102
- **来源 PR**: feat: 增加从token获取userId的便捷方法22222245a
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:32-42
- **描述**: 新增的 parseToken 方法（第32-42行）与下方已有的 parseToken 方法功能完全重复，导致代码冗余。虽然不会直接引发安全漏洞，但冗余代码增加了维护成本和潜在的逻辑不一致风险。这违反了 DRY（Don't Repeat Yourself）原则，后续开发者不清楚应该使用哪个方法，且修改其中一个时容易遗漏另一个。
- **修复**: 删除新增的重复方法（第32-42行），保留原有的 parseToken 方法。

### 案例 3
- **日期**: 2026-06-04 17202
- **来源 PR**: feat: 增加两个新方法
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:64
- **描述**: getUserIdFromToken 方法直接调用 parseToken 方法，但未处理 parseToken 可能抛出的异常（如 JwtException、ExpiredJwtException 等）。如果调用方期望该方法不会抛出异常，则需要在方法签名中声明异常或在方法内部捕获处理。当前方法签名未声明任何异常，调用方可能不会预期到运行时异常。
- **修复**: 考虑在 getUserIdFromToken 方法内部捕获 parseToken 可能抛出的异常，并返回 Optional<Long> 或抛出更具体的业务异常，以提高调用方的使用体验。

### 案例 4
- **日期**: 2026-06-04 17292
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:45-48
- **描述**: UserContext 中新增的 parseToken 方法（第45-48行）与 JwtUtil 中已有的 parseToken 方法（被多处引用，共7处）同名。虽然 UserContext.parseToken 只是委托给 JwtUtil.parseToken，但：1) 在 UserContext 中暴露 Claims 对象（JWT 内部实现细节）违反了封装原则，调用方本应通过更高层级的抽象（如
- **修复**: 考虑在 UserContext 中提供更高层级的封装方法（如 getUserIdFromToken(String token)），而不是直接暴露 Claims 对象。如果确实需要暴露，建议使用不同的方法名以避免混淆，并添加明确的文档说明。

### 案例 5
- **日期**: 2026-06-04 17292
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:18-50
- **描述**: UserContext 类新增的 getTokenRemainingTime、generateToken、parseToken 三个方法，均直接委托给 JwtUtil 的同名方法，没有添加任何额外逻辑（如缓存、日志、权限校验等）。这引入了一层不必要的间接调用，增加了调用栈深度和代码维护成本。每次调用都会多一次方法调用开销（虽然微乎其微），但更重要的是，这种设计会让开发者困惑：应该调用 UserCo
- **修复**: 如果这些方法只是简单的委托，建议直接删除 UserContext 中的这些方法，让调用方直接使用 JwtUtil 的静态方法。如果确实需要封装层，建议在 UserContext 中添加有实际价值的逻辑（如缓存 token 剩余时间、记录调用日志等）。

### 案例 6
- **日期**: 2026-06-04 17292
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:81-101
- **描述**: 新增的 getRemainingTime 方法（第81-101行）在当前 PR 中仅在 UserContext 的 getTokenRemainingTime 中被委托调用，而 UserContext 中的委托方法本身也应被移除（见上一条建议）。如果移除 UserContext 中的委托方法，则 getRemainingTime 方法在当前代码库中将没有任何直接调用方。虽然该方法可能是为未来使用而
- **修复**: 1) 如果该方法是为后续 PR 准备的，建议在同一个 PR 中包含调用方代码，确保变更的完整性；2) 如果当前确实没有调用方，考虑移除该方法，待需要时再添加。

### 案例 7
- **日期**: 2026-06-04 17381
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:33-39
- **描述**: UserContext.parseToken 方法声明返回类型为 Claims，但当前 diff 上下文中未显示 JwtUtil.parseToken 的返回类型。如果 JwtUtil.parseToken 的返回类型不是 Claims，或者 JwtUtil 类中不存在 parseToken 方法，将导致编译错误。此外，UserContext 类当前没有 import io.jsonwebtoke
- **修复**: 1) 确认 JwtUtil.parseToken 方法确实存在且返回 Claims 类型；2) 在 UserContext.java 中添加 import io.jsonwebtoken.Claims; 语句；3) 考虑删除此委托方法，让调用方直接使用 JwtUtil.parseToken。

### 案例 8
- **日期**: 2026-06-04 17381
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:18-23
- **描述**: 新增的 UserContext.getTokenRemainingTime(String token) 方法（第18-23行）仅直接委托调用 JwtUtil.getRemainingTime(token)，没有任何额外逻辑处理。这创建了一个不必要的委托层，增加了调用链长度和维护成本，却没有带来任何价值。
- **修复**: 建议直接删除 UserContext.getTokenRemainingTime 方法，让调用方直接使用 JwtUtil.getRemainingTime。如果确实需要保持 UserContext 作为统一入口，可以考虑在方法中添加额外逻辑（如参数校验、日志、缓存等）来证明其存在的必要性。

### 案例 9
- **日期**: 2026-06-04 17381
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:25-31
- **描述**: 新增的 UserContext.generateToken(Long userId) 方法（第25-31行）仅直接委托调用 JwtUtil.createToken(userId)，没有任何额外逻辑处理。这创建了一个不必要的委托层，增加了调用链长度和维护成本，却没有带来任何价值。
- **修复**: 建议直接删除 UserContext.generateToken 方法，让调用方直接使用 JwtUtil.createToken。如果确实需要保持 UserContext 作为统一入口，可以考虑在方法中添加额外逻辑（如参数校验、日志、缓存等）来证明其存在的必要性。

### 案例 10
- **日期**: 2026-06-04 17381
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:84-100
- **描述**: 新增的 JwtUtil.getRemainingTime(String token) 方法（第84-100行）在当前 PR 中仅被 UserContext.getTokenRemainingTime 调用，而 UserContext.getTokenRemainingTime 本身也是一个不必要的委托层。如果删除 UserContext 中的委托方法，则 getRemainingTime 在当前代
- **修复**: 1) 如果 getRemainingTime 是为未来使用而添加的，建议在同一个 PR 中包含实际调用方代码；2) 如果当前确实没有调用方，考虑移除该方法，待需要时再添加。

### 案例 11
- **日期**: 2026-06-04 17384
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:45-52
- **描述**: JwtUtil 类中 parseToken 方法被定义了两次（第36-42行和第45-52行），两个方法签名和实现完全一致。这会导致编译错误（Java 不允许同一类中存在两个相同签名的方法），PR 无法通过编译。
- **修复**: 删除第45-52行的重复 parseToken 方法定义，只保留第36-42行的原始定义。

### 案例 12
- **日期**: 2026-06-04 17384
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:20-24
- **描述**: UserContext.getTokenRemainingTime(String token) 方法（第20-24行）仅直接调用 JwtUtil.getRemainingTime(token) 并返回结果，没有任何额外逻辑。这是一个纯委托方法，增加了不必要的调用层级，违反了 DRY 原则。
- **修复**: 考虑删除此委托方法，让调用方直接使用 JwtUtil.getRemainingTime(token)。如果必须保留，建议添加业务逻辑或参数转换。

### 案例 13
- **日期**: 2026-06-04 17384
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:35-41
- **描述**: UserContext.parseToken(String token) 方法（第35-41行）仅直接调用 JwtUtil.parseToken(token) 并返回结果，没有任何额外逻辑。这是一个纯委托方法，增加了不必要的调用层级。
- **修复**: 考虑删除此委托方法，让调用方直接使用 JwtUtil.parseToken(token)。如果必须保留，建议添加业务逻辑或参数转换。

### 案例 14
- **日期**: 2026-06-04 17455
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:30-32
- **描述**: UserContext.generateToken(userId) 方法仅直接调用 JwtUtil.createToken(userId)，没有添加任何额外逻辑。这创建了一个不必要的委托层。调用方可以直接使用 JwtUtil.createToken(userId) 达到相同效果。
- **修复**: 删除 UserContext.generateToken 方法，让调用方直接使用 JwtUtil.createToken。如果确实需要封装，应添加额外业务逻辑。

### 案例 15
- **日期**: 2026-06-04 17455
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:38-40
- **描述**: UserContext.parseToken(token) 方法仅直接调用 JwtUtil.parseToken(token)，没有添加任何额外逻辑。这创建了一个不必要的委托层。调用方可以直接使用 JwtUtil.parseToken(token) 达到相同效果。
- **修复**: 删除 UserContext.parseToken 方法，让调用方直接使用 JwtUtil.parseToken。如果确实需要封装，应添加额外业务逻辑。

### 案例 16
- **日期**: 2026-06-04 17455
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:22-40
- **描述**: 根据 CodeGraph 分析结果，UserContext 新增的三个方法（getTokenRemainingTime、generateToken、parseToken）目前没有被任何外部文件调用。现有调用方（UserController、LoginInterceptor）直接使用 JwtUtil 的方法。这些新增方法在当前 PR 中是孤立的，没有实际用途。
- **修复**: 确认这些方法是否为未来功能预留。如果是，建议在需要时再添加，避免引入未使用的代码。如果确实需要，建议直接放在 JwtUtil 中而不是 UserContext。

### 案例 17
- **日期**: 2026-06-04 17455
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/UserContext.java`:44-47
- **描述**: UserContext 新增的 parseToken 方法直接返回 JwtUtil.parseToken(token) 的结果（Claims 对象）。Claims 对象包含 JWT 的所有声明（包括 userId、过期时间等），将其直接暴露给调用方可能增加安全风险。如果调用方误用或泄露 Claims 中的敏感信息，可能导致安全问题。建议考虑只返回必要的信息（如 userId），而不是整个 Clai
- **修复**: 将 parseToken 方法改为只返回 userId，或者创建一个只包含必要字段的 DTO 对象返回。例如：public static Long getUserIdFromToken(String token) { return JwtUtil.parseToken(token).get("userId", Long.class); }
