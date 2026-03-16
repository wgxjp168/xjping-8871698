package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/ilbuy/cart-svc/internal/config"
	"github.com/ilbuy/cart-svc/internal/handler"
	"github.com/ilbuy/cart-svc/internal/middleware"
	"github.com/ilbuy/cart-svc/internal/repository"
	"github.com/ilbuy/cart-svc/internal/service"
)

func main() {
	cfg := config.Load()

	// Redis 连接
	rdb := repository.NewRedisClient(cfg.Redis)
	cartRepo := repository.NewCartRepository(rdb, cfg.Cart.TTL)
	cartSvc := service.NewCartService(cartRepo)
	cartHandler := handler.NewCartHandler(cartSvc)

	// 路由
	r := handler.NewRouter(cartHandler, middleware.UserAuth(), middleware.Logger())

	srv := &http.Server{
		Addr:         ":" + cfg.Server.Port,
		Handler:      r,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// 优雅关闭
	go func() {
		log.Printf("cart-svc listening on :%s", cfg.Server.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen error: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down cart-svc...")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatalf("forced shutdown: %v", err)
	}
	log.Println("cart-svc exited")
}
