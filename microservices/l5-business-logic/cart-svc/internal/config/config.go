package config

import (
	"os"
	"strconv"
	"time"
)

// Config 服务配置
type Config struct {
	Server ServerConfig
	Redis  RedisConfig
	Cart   CartConfig
}

type ServerConfig struct {
	Port string
	Mode string // gin mode: debug / release / test
}

type RedisConfig struct {
	Host     string
	Port     string
	Password string
	DB       int
}

type CartConfig struct {
	// 购物车 Redis key 过期时间，默认 7 天
	TTL time.Duration
}

// Load 从环境变量加载，未设置则使用默认值
func Load() *Config {
	return &Config{
		Server: ServerConfig{
			Port: getEnv("SERVER_PORT", "8025"),
			Mode: getEnv("GIN_MODE", "release"),
		},
		Redis: RedisConfig{
			Host:     getEnv("REDIS_HOST", "localhost"),
			Port:     getEnv("REDIS_PORT", "6379"),
			Password: getEnv("REDIS_PASS", ""),
			DB:       getEnvInt("REDIS_DB", 0),
		},
		Cart: CartConfig{
			TTL: getEnvDuration("CART_TTL", 7*24*time.Hour),
		},
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if i, err := strconv.Atoi(v); err == nil {
			return i
		}
	}
	return fallback
}

func getEnvDuration(key string, fallback time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
	}
	return fallback
}
