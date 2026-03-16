package middleware

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

const (
	// ContextUserID gin.Context key，由本中间件注入
	ContextUserID = "userId"

	// Gateway 注入的请求头（网关已验证 JWT，这里直接信任）
	headerUserID   = "X-User-Id"
	headerUserRole = "X-User-Role"
	headerUsername = "X-Username"
)

// UserAuth 从 Gateway 注入的请求头中提取 userId
// 若直接访问（绕过 Gateway）则拒绝
func UserAuth() gin.HandlerFunc {
	return func(c *gin.Context) {
		rawID := c.GetHeader(headerUserID)
		if rawID == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"code":    http.StatusUnauthorized,
				"message": "缺少身份信息，请通过 API Gateway 访问",
			})
			return
		}

		userID, err := strconv.ParseInt(rawID, 10, 64)
		if err != nil || userID <= 0 {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{
				"code":    http.StatusUnauthorized,
				"message": "身份信息无效",
			})
			return
		}

		c.Set(ContextUserID, userID)
		c.Set("userRole", c.GetHeader(headerUserRole))
		c.Set("username", c.GetHeader(headerUsername))
		c.Next()
	}
}

// GetUserID 从 gin.Context 安全获取 userId
func GetUserID(c *gin.Context) int64 {
	if v, exists := c.Get(ContextUserID); exists {
		if id, ok := v.(int64); ok {
			return id
		}
	}
	return 0
}
