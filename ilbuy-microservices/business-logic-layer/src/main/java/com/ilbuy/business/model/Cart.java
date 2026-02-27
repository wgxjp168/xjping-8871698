package com.ilbuy.business.model;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

public class Cart {

    private String userId;
    private List<CartItem> items = new ArrayList<>();

    public Cart() {}

    public Cart(String userId) {
        this.userId = userId;
    }

    public void addItem(CartItem item) {
        Optional<CartItem> existing = items.stream()
                .filter(i -> i.getProductId().equals(item.getProductId()))
                .findFirst();
        if (existing.isPresent()) {
            existing.get().setQuantity(existing.get().getQuantity() + item.getQuantity());
        } else {
            items.add(item);
        }
    }

    public boolean removeItem(String productId) {
        return items.removeIf(i -> i.getProductId().equals(productId));
    }

    public double getTotalAmount() {
        return Math.round(items.stream().mapToDouble(CartItem::getSubtotal).sum() * 100.0) / 100.0;
    }

    public int getTotalItems() {
        return items.stream().mapToInt(CartItem::getQuantity).sum();
    }

    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
    public List<CartItem> getItems() { return items; }
    public void setItems(List<CartItem> items) { this.items = items; }
}
