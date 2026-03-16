package repository

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/ilbuy/cart-svc/internal/model"
	"github.com/redis/go-redis/v9"
)

// CartRepository Redis Hash 实现
// 数据结构: HSET cart:{userId}  "{canonicalId}:{platform}"  <CartItem JSON>
// 过期策略: 每次写操作重置 TTL
type CartRepository struct {
	rdb *redis.Client
	ttl time.Duration
}

func NewCartRepository(rdb *redis.Client, ttl time.Duration) *CartRepository {
	return &CartRepository{rdb: rdb, ttl: ttl}
}

func cartKey(userID int64) string {
	return fmt.Sprintf("cart:%d", userID)
}

// GetAll 返回用户全部购物车条目
func (r *CartRepository) GetAll(ctx context.Context, userID int64) ([]*model.CartItem, error) {
	fields, err := r.rdb.HGetAll(ctx, cartKey(userID)).Result()
	if err != nil {
		return nil, err
	}
	items := make([]*model.CartItem, 0, len(fields))
	for _, v := range fields {
		var item model.CartItem
		if err := json.Unmarshal([]byte(v), &item); err != nil {
			continue // 跳过损坏数据
		}
		items = append(items, &item)
	}
	return items, nil
}

// GetItem 获取单条购物车商品，不存在返回 nil, nil
func (r *CartRepository) GetItem(ctx context.Context, userID int64, fieldKey string) (*model.CartItem, error) {
	val, err := r.rdb.HGet(ctx, cartKey(userID), fieldKey).Result()
	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var item model.CartItem
	if err := json.Unmarshal([]byte(val), &item); err != nil {
		return nil, err
	}
	return &item, nil
}

// Save 新增或覆盖一条购物车商品，并刷新 TTL
func (r *CartRepository) Save(ctx context.Context, userID int64, item *model.CartItem) error {
	data, err := json.Marshal(item)
	if err != nil {
		return err
	}
	key := cartKey(userID)
	pipe := r.rdb.Pipeline()
	pipe.HSet(ctx, key, item.Key(), data)
	pipe.Expire(ctx, key, r.ttl)
	_, err = pipe.Exec(ctx)
	return err
}

// Remove 删除一条购物车商品
func (r *CartRepository) Remove(ctx context.Context, userID int64, fieldKey string) error {
	return r.rdb.HDel(ctx, cartKey(userID), fieldKey).Err()
}

// Clear 清空整个购物车
func (r *CartRepository) Clear(ctx context.Context, userID int64) error {
	return r.rdb.Del(ctx, cartKey(userID)).Err()
}

// Count 返回购物车商品种类数
func (r *CartRepository) Count(ctx context.Context, userID int64) (int64, error) {
	return r.rdb.HLen(ctx, cartKey(userID)).Result()
}
