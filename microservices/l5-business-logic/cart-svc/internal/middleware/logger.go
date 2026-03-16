package middleware

import (
	"log"
	"time"

	"github.com/gin-gonic/gin"
)

// Logger 请求日志中间件
func Logger() gin.HandlerFunc {
	return func(c *gin.Context) {
		start  := time.Now()
		path   := c.Request.URL.Path
		method := c.Request.Method

		c.Next()

		elapsed := time.Since(start)
		status  := c.Writer.Status()
		userID  := GetUserID(c)

		log.Printf("[cart-svc] %s %s | status=%d | userId=%d | %v",
			method, path, status, userID, elapsed)
	}
}
