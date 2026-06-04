"""测试影响力分级 - 高影响场景"""
from src.tools.impact_classifier import classify_changes, build_impact_report

diff = '''diff --git a/src/main/java/com/study/room/utils/JwtUtil.java b/src/main/java/com/study/room/utils/JwtUtil.java
@@ -20,8 +20,7 @@ public class JwtUtil {
-    public static String createToken(Long userId) {
+    public static String createToken() {
         Map<String, Object> claims = new HashMap<>();
-        claims.put("userId", userId);
     }
diff --git a/src/main/java/com/study/room/interceptor/LoginInterceptor.java b/src/main/java/com/study/room/interceptor/LoginInterceptor.java
@@ -4,6 +4,7 @@ import com.study.room.utils.JwtUtil;
+    // asdasd5466556
'''

skip, light, deep = classify_changes(diff, 'F:/PRtest/testagentPR', deep_threshold=1)
print(build_impact_report(skip, light, deep))
print(f'=== 汇总: 跳过={len(skip)} | 轻量={len(light)} | 深挖={len(deep)} ===')
for d in deep:
    print(f'[深挖] {d.symbol} - {d.reason}')
    for c in d.callers:
        print(f'  调用方: {c["name"]} ({c["filePath"]})')
