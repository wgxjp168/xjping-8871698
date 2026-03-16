package model

import (
	"time"

	"github.com/shopspring/decimal"
)

// CartItem 购物车单个商品行（含跨平台比价信息）
type CartItem struct {
	// 来自 L4 data-svc 的跨平台唯一 ID
	CanonicalID  string          `json:"canonicalId"  binding:"required"`
	// 商品来源平台（jd / taobao / pdd / …）
	Platform     string          `json:"platform"     binding:"required"`
	ProductTitle string          `json:"productTitle" binding:"required"`
	UnitPrice    decimal.Decimal `json:"unitPrice"    binding:"required"`
	Quantity     int             `json:"quantity"     binding:"required,min=1,max=999"`
	// 规格快照 JSON，如 {"颜色":"黑色","存储":"256GB"}
	Specs        string          `json:"specs,omitempty"`
	ImageURL     string          `json:"imageUrl,omitempty"`
	AddedAt      time.Time       `json:"addedAt"`
	UpdatedAt    time.Time       `json:"updatedAt"`
}

// CartItemKey 购物车 Hash field 唯一键（同一 canonicalId 在不同平台算不同行）
func (c *CartItem) Key() string {
	return c.CanonicalID + ":" + c.Platform
}

// Subtotal 单行小计
func (c *CartItem) Subtotal() decimal.Decimal {
	return c.UnitPrice.Mul(decimal.NewFromInt(int64(c.Quantity)))
}

// Cart 用户购物车聚合视图
type Cart struct {
	UserID    int64       `json:"userId"`
	Items     []*CartItem `json:"items"`
	Total     decimal.Decimal `json:"total"`
	ItemCount int         `json:"itemCount"`
}

// AddItemRequest 加购请求
type AddItemRequest struct {
	CanonicalID  string          `json:"canonicalId"  binding:"required"`
	Platform     string          `json:"platform"     binding:"required"`
	ProductTitle string          `json:"productTitle" binding:"required"`
	UnitPrice    decimal.Decimal `json:"unitPrice"    binding:"required"`
	Quantity     int             `json:"quantity"     binding:"required,min=1,max=999"`
	Specs        string          `json:"specs,omitempty"`
	ImageURL     string          `json:"imageUrl,omitempty"`
}

// UpdateQuantityRequest 更新数量请求
type UpdateQuantityRequest struct {
	Quantity int `json:"quantity" binding:"required,min=1,max=999"`
}

// ErrorResponse 统一错误响应
type ErrorResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}
