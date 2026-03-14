package config

import "os"

// Config 存储适配服务配置
type Config struct {
	Env  string
	Port string

	// MySQL
	MySQLDSN string

	// Redis
	RedisAddr     string
	RedisPassword string
	RedisDB       int

	// Elasticsearch
	ESAddresses []string
	ESUsername  string
	ESPassword  string

	// MinIO
	MinIOEndpoint  string
	MinIOAccessKey string
	MinIOSecretKey string
	MinIOBucket    string

	// ClickHouse
	ClickHouseDSN string
}

func Load() *Config {
	return &Config{
		Env:  getEnv("APP_ENV", "development"),
		Port: getEnv("PORT", "8035"),

		MySQLDSN: getEnv("MYSQL_DSN",
			"root:ilbuy@2024@tcp(localhost:3306)/ilbuy_main?charset=utf8mb4&parseTime=True"),

		RedisAddr:     getEnv("REDIS_HOST", "localhost") + ":6379",
		RedisPassword: getEnv("REDIS_PASSWORD", "ilbuy@2024"),

		ESAddresses: []string{getEnv("ES_HOST", "http://localhost:9200")},

		MinIOEndpoint:  getEnv("MINIO_HOST", "localhost:9000"),
		MinIOAccessKey: getEnv("MINIO_ACCESS_KEY", "ilbuy"),
		MinIOSecretKey: getEnv("MINIO_SECRET_KEY", "ilbuy@2024"),
		MinIOBucket:    getEnv("MINIO_BUCKET", "ilbuy-reports"),

		ClickHouseDSN: getEnv("CLICKHOUSE_DSN", "clickhouse://localhost:9000/ilbuy"),
	}
}

func getEnv(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}
