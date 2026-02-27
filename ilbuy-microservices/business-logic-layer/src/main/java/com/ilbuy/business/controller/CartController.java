package com.ilbuy.business.controller;

import com.ilbuy.business.model.Cart;
import com.ilbuy.business.service.CartService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/cart")
public class CartController {

    private final CartService cartService;

    public CartController(CartService cartService) {
        this.cartService = cartService;
    }

    @GetMapping("/{userId}")
    public ResponseEntity<Cart> getCart(@PathVariable String userId) {
        return ResponseEntity.ok(cartService.getCart(userId));
    }

    @PostMapping("/{userId}/items")
    public ResponseEntity<Cart> addToCart(
            @PathVariable String userId,
            @RequestBody Map<String, Object> body) {
        String productId = (String) body.get("productId");
        int quantity = ((Number) body.getOrDefault("quantity", 1)).intValue();
        return ResponseEntity.ok(cartService.addToCart(userId, productId, quantity));
    }

    @DeleteMapping("/{userId}/items/{productId}")
    public ResponseEntity<Cart> removeFromCart(
            @PathVariable String userId,
            @PathVariable String productId) {
        return ResponseEntity.ok(cartService.removeFromCart(userId, productId));
    }

    @DeleteMapping("/{userId}")
    public ResponseEntity<Void> clearCart(@PathVariable String userId) {
        cartService.clearCart(userId);
        return ResponseEntity.noContent().build();
    }
}
