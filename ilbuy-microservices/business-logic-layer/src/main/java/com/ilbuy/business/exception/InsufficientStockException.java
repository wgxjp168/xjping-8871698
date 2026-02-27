package com.ilbuy.business.exception;

public class InsufficientStockException extends RuntimeException {
    public InsufficientStockException(String productId, int requested, int available) {
        super("商品 %s 库存不足: 请求 %d, 可用 %d".formatted(productId, requested, available));
    }
}
