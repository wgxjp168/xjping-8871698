package com.ilbuy.business.model;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

public class Order {

    private String id;
    private String userId;
    private List<OrderItem> items = new ArrayList<>();
    private double totalAmount;
    private String status;
    private String shippingAddress;
    private String paymentMethod;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public Order() {}

    public Order(String id, String userId) {
        this.id = id;
        this.userId = userId;
        this.status = "PENDING";
        this.createdAt = LocalDateTime.now();
        this.updatedAt = LocalDateTime.now();
    }

    public void addItem(OrderItem item) {
        this.items.add(item);
        recalculateTotal();
    }

    public void recalculateTotal() {
        this.totalAmount = items.stream()
                .mapToDouble(i -> i.getPrice() * i.getQuantity())
                .sum();
        this.totalAmount = Math.round(this.totalAmount * 100.0) / 100.0;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
    public List<OrderItem> getItems() { return items; }
    public void setItems(List<OrderItem> items) { this.items = items; }
    public double getTotalAmount() { return totalAmount; }
    public void setTotalAmount(double totalAmount) { this.totalAmount = totalAmount; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; this.updatedAt = LocalDateTime.now(); }
    public String getShippingAddress() { return shippingAddress; }
    public void setShippingAddress(String shippingAddress) { this.shippingAddress = shippingAddress; }
    public String getPaymentMethod() { return paymentMethod; }
    public void setPaymentMethod(String paymentMethod) { this.paymentMethod = paymentMethod; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
