package handler

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/ilbuy/cart-svc/internal/middleware"
	"github.com/ilbuy/cart-svc/internal/model"
	"github.com/ilbuy/cart-svc/internal/service"
)

// CartHandler HTTP 处理器
type CartHandler struct {
	svc *service.CartService
}

func NewCartHandler(svc *service.CartService) *CartHandler {
	return &CartHandler{svc: svc}
}

// GetCart GET /api/v1/cart
// @Summary 查询当前用户购物车
func (h *CartHandler) GetCart(c *gin.Context) {
	userID := middleware.GetUserID(c)
	cart, err := h.svc.GetCart(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, errResp(err))
		return
	}
	c.JSON(http.StatusOK, cart)
}

// AddItem POST /api/v1/cart/items
// @Summary 加购商品（已存在则数量累加）
func (h *CartHandler) AddItem(c *gin.Context) {
	var req model.AddItemRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errMsg(err.Error()))
		return
	}

	userID := middleware.GetUserID(c)
	cart, err := h.svc.AddItem(c.Request.Context(), userID, &req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, errResp(err))
		return
	}
	c.JSON(http.StatusOK, cart)
}

// UpdateQuantity PUT /api/v1/cart/items
// @Summary 修改购物车某商品数量
// @Param   canonicalId query string true "跨平台商品ID"
// @Param   platform    query string true "平台标识"
func (h *CartHandler) UpdateQuantity(c *gin.Context) {
	canonicalID := c.Query("canonicalId")
	platform    := c.Query("platform")
	if canonicalID == "" || platform == "" {
		c.JSON(http.StatusBadRequest, errMsg("canonicalId 和 platform 为必填查询参数"))
		return
	}

	var req model.UpdateQuantityRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, errMsg(err.Error()))
		return
	}

	userID := middleware.GetUserID(c)
	cart, err := h.svc.UpdateQuantity(c.Request.Context(), userID, canonicalID, platform, req.Quantity)
	if err != nil {
		if errors.Is(err, service.ErrItemNotFound) {
			c.JSON(http.StatusNotFound, errResp(err))
			return
		}
		c.JSON(http.StatusInternalServerError, errResp(err))
		return
	}
	c.JSON(http.StatusOK, cart)
}

// RemoveItem DELETE /api/v1/cart/items
// @Summary 移除购物车单行商品
// @Param   canonicalId query string true "跨平台商品ID"
// @Param   platform    query string true "平台标识"
func (h *CartHandler) RemoveItem(c *gin.Context) {
	canonicalID := c.Query("canonicalId")
	platform    := c.Query("platform")
	if canonicalID == "" || platform == "" {
		c.JSON(http.StatusBadRequest, errMsg("canonicalId 和 platform 为必填查询参数"))
		return
	}

	userID := middleware.GetUserID(c)
	cart, err := h.svc.RemoveItem(c.Request.Context(), userID, canonicalID, platform)
	if err != nil {
		if errors.Is(err, service.ErrItemNotFound) {
			c.JSON(http.StatusNotFound, errResp(err))
			return
		}
		c.JSON(http.StatusInternalServerError, errResp(err))
		return
	}
	c.JSON(http.StatusOK, cart)
}

// ClearCart DELETE /api/v1/cart
// @Summary 清空购物车
func (h *CartHandler) ClearCart(c *gin.Context) {
	userID := middleware.GetUserID(c)
	if err := h.svc.ClearCart(c.Request.Context(), userID); err != nil {
		c.JSON(http.StatusInternalServerError, errResp(err))
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "购物车已清空"})
}

// GetCount GET /api/v1/cart/count
// @Summary 获取购物车商品种类数
func (h *CartHandler) GetCount(c *gin.Context) {
	userID := middleware.GetUserID(c)
	count, err := h.svc.GetCount(c.Request.Context(), userID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, errResp(err))
		return
	}
	c.JSON(http.StatusOK, gin.H{"count": count})
}

// ── 工具 ─────────────────────────────────────────────────────

func errResp(err error) gin.H {
	return gin.H{"code": http.StatusInternalServerError, "message": err.Error()}
}

func errMsg(msg string) gin.H {
	return gin.H{"code": http.StatusBadRequest, "message": msg}
}
