package com.ilbuy.data.controller;

import com.ilbuy.data.entity.*;
import com.ilbuy.data.service.*;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/data")
public class DataController {

    private final DataUserService userService;
    private final DataProductService productService;
    private final DataOrderService orderService;

    public DataController(DataUserService userService, DataProductService productService, DataOrderService orderService) {
        this.userService = userService;
        this.productService = productService;
        this.orderService = orderService;
    }

    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> status() {
        return ResponseEntity.ok(Map.of(
                "service", "ILbuy Data Layer",
                "status", "running",
                "database", "H2 (in-memory)",
                "tables", List.of("users", "products", "orders", "order_items"),
                "timestamp", LocalDateTime.now().toString()
        ));
    }

    // --- Users ---
    @GetMapping("/users")
    public List<UserEntity> listUsers() { return userService.findAll(); }

    @GetMapping("/users/{id}")
    public UserEntity getUser(@PathVariable String id) { return userService.findById(id); }

    @PostMapping("/users")
    public ResponseEntity<UserEntity> createUser(@RequestBody UserEntity user) {
        return ResponseEntity.status(HttpStatus.CREATED).body(userService.save(user));
    }

    // --- Products ---
    @GetMapping("/products")
    public List<ProductEntity> listProducts(@RequestParam(required = false) String category) {
        if (category != null) return productService.findByCategory(category);
        return productService.findAll();
    }

    @GetMapping("/products/{id}")
    public ProductEntity getProduct(@PathVariable String id) { return productService.findById(id); }

    @GetMapping("/products/search")
    public List<ProductEntity> searchProducts(@RequestParam String q) { return productService.search(q); }

    @PostMapping("/products")
    public ResponseEntity<ProductEntity> createProduct(@RequestBody ProductEntity product) {
        return ResponseEntity.status(HttpStatus.CREATED).body(productService.save(product));
    }

    // --- Orders ---
    @GetMapping("/orders")
    public List<OrderEntity> listOrders(@RequestParam(required = false) String userId) {
        if (userId != null) return orderService.findByUserId(userId);
        return orderService.findAll();
    }

    @GetMapping("/orders/{id}")
    public OrderEntity getOrder(@PathVariable String id) { return orderService.findById(id); }

    @PostMapping("/orders")
    public ResponseEntity<OrderEntity> createOrder(@RequestBody OrderEntity order) {
        return ResponseEntity.status(HttpStatus.CREATED).body(orderService.save(order));
    }

    // --- Stats ---
    @GetMapping("/stats")
    public Map<String, Object> stats() {
        return Map.of(
                "userCount", userService.findAll().size(),
                "productCount", productService.findAll().size(),
                "orderCount", orderService.findAll().size()
        );
    }
}
