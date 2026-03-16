package service

import (
	"context"
	"errors"
	"sort"
	"time"

	"github.com/ilbuy/cart-svc/internal/model"
	"github.com/ilbuy/cart-svc/internal/repository"
	"github.com/shopspring/decimal"
)

var (
	ErrItemNotFound  = errors.New("购物车中不存在该商品")
	ErrEmptyCart     = errors.New("购物车为空")
)

// CartService 购物车业务逻辑
type CartService struct {
	repo *repository.CartRepository
}

func NewCartService(repo *repository.CartRepository) *CartService {
	return &CartService{repo: repo}
}

// GetCart 查询用户购物车（按加购时间倒序）
func (s *CartService) GetCart(ctx context.Context, userID int64) (*model.Cart, error) {
	items, err := s.repo.GetAll(ctx, userID)
	if err != nil {
		return nil, err
	}
	return buildCart(userID, items), nil
}

// AddItem 加购或合并数量
// - 同一 canonicalId+platform 已存在：数量累加，价格更新为最新
// - 否则新建行
func (s *CartService) AddItem(ctx context.Context, userID int64, req *model.AddItemRequest) (*model.Cart, error) {
	fieldKey := req.CanonicalID + ":" + req.Platform

	existing, err := s.repo.GetItem(ctx, userID, fieldKey)
	if err != nil {
		return nil, err
	}

	var item *model.CartItem
	now := time.Now()
	if existing != nil {
		// 合并：数量累加，价格以最新为准
		item = existing
		item.Quantity    += req.Quantity
		item.UnitPrice    = req.UnitPrice
		item.ProductTitle = req.ProductTitle
		item.ImageURL     = req.ImageURL
		if req.Specs != "" {
			item.Specs = req.Specs
		}
		item.UpdatedAt = now
	} else {
		item = &model.CartItem{
			CanonicalID:  req.CanonicalID,
			Platform:     req.Platform,
			ProductTitle: req.ProductTitle,
			UnitPrice:    req.UnitPrice,
			Quantity:     req.Quantity,
			Specs:        req.Specs,
			ImageURL:     req.ImageURL,
			AddedAt:      now,
			UpdatedAt:    now,
		}
	}

	if err := s.repo.Save(ctx, userID, item); err != nil {
		return nil, err
	}
	return s.GetCart(ctx, userID)
}

// UpdateQuantity 修改单行数量（quantity=0 不允许，应调用 RemoveItem）
func (s *CartService) UpdateQuantity(ctx context.Context, userID int64, canonicalID, platform string, quantity int) (*model.Cart, error) {
	fieldKey := canonicalID + ":" + platform

	item, err := s.repo.GetItem(ctx, userID, fieldKey)
	if err != nil {
		return nil, err
	}
	if item == nil {
		return nil, ErrItemNotFound
	}

	item.Quantity  = quantity
	item.UpdatedAt = time.Now()

	if err := s.repo.Save(ctx, userID, item); err != nil {
		return nil, err
	}
	return s.GetCart(ctx, userID)
}

// RemoveItem 移除单行商品
func (s *CartService) RemoveItem(ctx context.Context, userID int64, canonicalID, platform string) (*model.Cart, error) {
	fieldKey := canonicalID + ":" + platform

	item, err := s.repo.GetItem(ctx, userID, fieldKey)
	if err != nil {
		return nil, err
	}
	if item == nil {
		return nil, ErrItemNotFound
	}

	if err := s.repo.Remove(ctx, userID, fieldKey); err != nil {
		return nil, err
	}
	return s.GetCart(ctx, userID)
}

// ClearCart 清空购物车
func (s *CartService) ClearCart(ctx context.Context, userID int64) error {
	return s.repo.Clear(ctx, userID)
}

// GetCount 返回商品种类数
func (s *CartService) GetCount(ctx context.Context, userID int64) (int64, error) {
	return s.repo.Count(ctx, userID)
}

// ── 私有工具 ──────────────────────────────────────────────────

func buildCart(userID int64, items []*model.CartItem) *model.Cart {
	// 按加购时间倒序排列
	sort.Slice(items, func(i, j int) bool {
		return items[i].AddedAt.After(items[j].AddedAt)
	})

	total := decimal.Zero
	for _, item := range items {
		total = total.Add(item.Subtotal())
	}

	return &model.Cart{
		UserID:    userID,
		Items:     items,
		Total:     total,
		ItemCount: len(items),
	}
}
