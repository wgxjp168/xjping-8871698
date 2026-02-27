package com.ilbuy.business.service;

import com.ilbuy.business.model.Cart;
import com.ilbuy.business.model.CartItem;
import com.ilbuy.business.model.Product;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;

@Service
public class CartService {

    private static final Logger log = LoggerFactory.getLogger(CartService.class);
    private final Map<String, Cart> carts = new ConcurrentHashMap<>();
    private final ProductService productService;

    public CartService(ProductService productService) {
        this.productService = productService;
    }

    public Cart getCart(String userId) {
        return carts.computeIfAbsent(userId, Cart::new);
    }

    public Cart addToCart(String userId, String productId, int quantity) {
        Product product = productService.findById(productId);
        Cart cart = getCart(userId);
        cart.addItem(new CartItem(product.getId(), product.getName(), product.getPrice(), quantity));
        log.info("加入购物车: userId={}, productId={}, qty={}", userId, productId, quantity);
        return cart;
    }

    public Cart removeFromCart(String userId, String productId) {
        Cart cart = getCart(userId);
        cart.removeItem(productId);
        log.info("移出购物车: userId={}, productId={}", userId, productId);
        return cart;
    }

    public void clearCart(String userId) {
        carts.remove(userId);
        log.info("清空购物车: userId={}", userId);
    }
}
