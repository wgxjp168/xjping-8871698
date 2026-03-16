package handler_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/ilbuy/cart-svc/internal/handler"
	"github.com/ilbuy/cart-svc/internal/middleware"
	"github.com/ilbuy/cart-svc/internal/model"
	"github.com/shopspring/decimal"
	"github.com/stretchr/testify/assert"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// stubCartService 简单桩，不依赖 Redis
type stubCartService struct{}

func (s *stubCartService) GetCart(_ interface{}, userID int64) (*model.Cart, error) {
	return &model.Cart{
		UserID: userID,
		Items: []*model.CartItem{
			{
				CanonicalID:  "c001",
				Platform:     "jd",
				ProductTitle: "iPhone 15",
				UnitPrice:    decimal.NewFromFloat(7999),
				Quantity:     1,
				AddedAt:      time.Now(),
			},
		},
		Total:     decimal.NewFromFloat(7999),
		ItemCount: 1,
	}, nil
}

// ── 测试用 Handler 包装 ──────────────────────────────────────

func newTestRouter() *gin.Engine {
	r := gin.New()

	// 注入伪造的 userId（模拟 Gateway 已鉴权）
	injectUser := func(c *gin.Context) {
		c.Request.Header.Set("X-User-Id", "42")
		c.Next()
	}

	v1 := r.Group("/api/v1/cart", injectUser, middleware.UserAuth())

	// 直接构建 handler（用真实 handler 结构，CartService 接口化）
	// 这里为简化直接测试路由注册 + 中间件行为
	v1.GET("", func(c *gin.Context) {
		userID := middleware.GetUserID(c)
		c.JSON(http.StatusOK, gin.H{"userId": userID, "itemCount": 1})
	})
	v1.GET("/count", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"count": 1})
	})
	return r
}

func TestGetCart_WithValidUserHeader(t *testing.T) {
	r := newTestRouter()

	req := httptest.NewRequest(http.MethodGet, "/api/v1/cart", nil)
	req.Header.Set("X-User-Id", "42")
	w := httptest.NewRecorder()

	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var body map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &body)
	assert.NoError(t, err)
	assert.Equal(t, float64(42), body["userId"])
}

func TestGetCart_WithoutUserHeader_Returns401(t *testing.T) {
	r := gin.New()
	r.GET("/api/v1/cart", middleware.UserAuth(), func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{})
	})

	req := httptest.NewRequest(http.MethodGet, "/api/v1/cart", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAddItem_InvalidBody_Returns400(t *testing.T) {
	r := gin.New()
	injectUser := func(c *gin.Context) {
		c.Request.Header.Set("X-User-Id", "42")
		c.Next()
	}
	r.POST("/api/v1/cart/items", injectUser, middleware.UserAuth(), func(c *gin.Context) {
		var req model.AddItemRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"code": 400, "message": err.Error()})
			return
		}
		c.JSON(http.StatusOK, gin.H{})
	})

	// 缺少必填字段
	body := bytes.NewBufferString(`{"quantity": 1}`)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/cart/items", body)
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestHealthEndpoint(t *testing.T) {
	r := handler.NewRouter(
		handler.NewCartHandler(nil), // handler methods not called in health check
		middleware.UserAuth(),
		middleware.Logger(),
	)

	req := httptest.NewRequest(http.MethodGet, "/actuator/health", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	var body map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &body)
	assert.Equal(t, "UP", body["status"])
}
