package repository

import (
	"fmt"

	"github.com/ilbuy/cart-svc/internal/config"
	"github.com/redis/go-redis/v9"
)

// NewRedisClient 创建 Redis 客户端
func NewRedisClient(cfg config.RedisConfig) *redis.Client {
	return redis.NewClient(&redis.Options{
		Addr:     fmt.Sprintf("%s:%s", cfg.Host, cfg.Port),
		Password: cfg.Password,
		DB:       cfg.DB,
		PoolSize: 10,
	})
}
