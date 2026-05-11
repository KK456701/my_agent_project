// Demo Go 代码 — 包含安全、性能、架构问题
package main

import (
    "database/sql"
    "fmt"
    "net/http"
    "os"
)

var secretKey = "my-hardcoded-key-12345" // 🔴 硬编码密钥

func loginUser(db *sql.DB, username string, password string) error {
    query := fmt.Sprintf("SELECT * FROM users WHERE name = '%s'", username) // 🔴 SQL 注入
    rows, err := db.Query(query)
    if err != nil {
        return err
    }
    defer rows.Close()
    
    _ = password // 🟡 忽略 password 参数
    return nil
}

func startServer() {
    go func() { // 🟡 goroutine 无退出机制
        for {
            http.Get("http://example.com") // 🔴 每次请求新建连接
        }
    }()
    
    http.ListenAndServe(":8080", nil)
}
