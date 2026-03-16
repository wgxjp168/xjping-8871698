package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// NewRouter 组装路由
func NewRouter(cart *CartHandler, authMiddleware ...gin.HandlerFunc) *gin.Engine {
	r := gin.New()
	r.Use(gin.Recovery())

	// 健康检查（无需鉴权）
	r.GET("/actuator/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "UP", "service": "cart-svc"})
	})

	// 购物车路由（全部需要鉴权）
	v1 := r.Group("/api/v1/cart", authMiddleware...)
	{
		v1.GET("",          cart.GetCart)      // 查看购物车
		v1.GET("/count",    cart.GetCount)     // 商品种类数
		v1.POST("/items",   cart.AddItem)      // 加购
		v1.PUT("/items",    cart.UpdateQuantity) // 改数量
		v1.DELETE("/items", cart.RemoveItem)   // 移除单行
		v1.DELETE("",       cart.ClearCart)    // 清空
	}

	return r
}
