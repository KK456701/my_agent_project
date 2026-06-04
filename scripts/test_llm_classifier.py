"""测试 DeepSeek 驱动的变更影响力分级"""
import sys
sys.path.insert(0, '.')

from src.tools.impact_classifier_llm import DeepSeekClassifier
from src.tools.impact_classifier import build_impact_report

# PR#1 的实际 diff 核心部分
diff = '''diff --git a/src/main/java/com/study/room/utils/JwtUtil.java b/src/main/java/com/study/room/utils/JwtUtil.java
@@ -35,6 +35,14 @@ public class JwtUtil {
         return Jwts.parserBuilder()
                 .setSigningKey(SECRET_KEY)
                 .build()
+                .parseClaimsJws(token)
+                .getBody();
+    }
+    //asdasd5466556
+
+    public static Claims parseToken(String token) {
+        return Jwts.parserBuilder()
+                .setSigningKey(SECRET_KEY)
+                .build()
                 .parseClaimsJws(token)
                 .getBody();
     }
diff --git a/src/main/java/com/study/room/utils/UserContext.java b/src/main/java/com/study/room/utils/UserContext.java
new file mode 100644
@@ -0,0 +1,18 @@
+package com.study.room.utils;
+
+public class UserContext {
+    private static final ThreadLocal<Long> THREAD_LOCAL = new ThreadLocal<>();
+
+    public static void setUser(Long userId) {
+        THREAD_LOCAL.set(userId);
+    }
+
+    public static Long getUser() {
+        return THREAD_LOCAL.get();
+    }
+
+    public static void removeUser() {
+        THREAD_LOCAL.remove();
+    }
+}
diff --git a/src/main/java/com/study/room/controller/UserController.java b/src/main/java/com/study/room/controller/UserController.java
@@ -4,6 +4,7 @@ import com.study.room.entity.User;
 import com.study.room.service.UserService;
 import com.study.room.utils.JwtUtil;
+import com.study.room.utils.UserContext;
 import org.springframework.beans.factory.annotation.Autowired;
@@ -27,6 +28,7 @@ public class UserController {
     @GetMapping("/{id}")
     public Result<User> getById(@PathVariable Long id) {
+        // Long currentLoginUser = UserContext.getUser();
         User user = userService.getById(id);
         return Result.success(user);
     }
'''

classifier = DeepSeekClassifier()
result = classifier.classify(diff, 'F:/PRtest/testagentPR', deep_threshold=2)

print("=" * 60)
print(f"DeepSeek 推理: {result.reasoning}")
print("=" * 60)
print(build_impact_report(result.skip, result.light, result.deep))

print("\n=== 详细分类 ===")
for d in result.deep:
    print(f"\n🔬 DEEP: {d.symbol} — {d.reason}")
    for c in d.callers:
        print(f"   → {c['name']} ({c['filePath']}:{c['startLine']})")

for l in result.light:
    print(f"\n🔍 LIGHT: {l.symbol} — {l.reason}")

for s in result.skip:
    print(f"\n⏭️ SKIP: {s.file} — {s.reason}")
