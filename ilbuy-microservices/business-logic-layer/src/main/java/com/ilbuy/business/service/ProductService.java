package com.ilbuy.business.service;

import com.ilbuy.business.exception.InsufficientStockException;
import com.ilbuy.business.exception.ResourceNotFoundException;
import com.ilbuy.business.model.Product;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@Service
public class ProductService {

    private static final Logger log = LoggerFactory.getLogger(ProductService.class);
    private final Map<String, Product> products = new ConcurrentHashMap<>();

    public ProductService() {
        addSample("P001", "智能手表Pro", "高清AMOLED屏幕，健康监测", "electronics", 1299.00, 200);
        addSample("P002", "无线降噪耳机", "主动降噪，40小时续航", "electronics", 899.00, 500);
        addSample("P003", "运动跑鞋飞翼", "轻量透气，碳板助力", "sports", 599.00, 300);
        addSample("P004", "有机绿茶礼盒", "明前特级，罐装礼盒", "food", 168.00, 1000);
        addSample("P005", "便携充电宝20000mAh", "双向快充，轻薄设计", "electronics", 199.00, 800);
        addSample("P006", "纯棉T恤", "舒适透气，多色可选", "clothing", 89.00, 2000);
        addSample("P007", "智能台灯", "护眼LED，色温调节", "home", 259.00, 150);
        addSample("P008", "蓝牙音箱", "IPX7防水，360°环绕音", "electronics", 349.00, 400);
    }

    private void addSample(String id, String name, String desc, String cat, double price, int stock) {
        products.put(id, new Product(id, name, desc, cat, price, stock));
    }

    public List<Product> findAll(String category) {
        if (category == null || category.isEmpty()) return new ArrayList<>(products.values());
        return products.values().stream()
                .filter(p -> p.getCategory().equalsIgnoreCase(category))
                .collect(Collectors.toList());
    }

    public Product findById(String id) {
        Product product = products.get(id);
        if (product == null) throw new ResourceNotFoundException("商品不存在: " + id);
        return product;
    }

    public Product create(Product product) {
        String id = "P" + String.format("%03d", products.size() + 1);
        product.setId(id);
        product.setCreatedAt(LocalDateTime.now());
        product.setUpdatedAt(LocalDateTime.now());
        if (product.getStatus() == null) product.setStatus("ON_SALE");
        products.put(id, product);
        log.info("创建商品: id={}, name={}, price={}", id, product.getName(), product.getPrice());
        return product;
    }

    public Product update(String id, Product updated) {
        Product product = findById(id);
        if (updated.getName() != null) product.setName(updated.getName());
        if (updated.getDescription() != null) product.setDescription(updated.getDescription());
        if (updated.getPrice() > 0) product.setPrice(updated.getPrice());
        if (updated.getStock() >= 0) product.setStock(updated.getStock());
        if (updated.getStatus() != null) product.setStatus(updated.getStatus());
        product.setUpdatedAt(LocalDateTime.now());
        log.info("更新商品: id={}", id);
        return product;
    }

    public void deductStock(String productId, int quantity) {
        Product product = findById(productId);
        if (product.getStock() < quantity) {
            throw new InsufficientStockException(productId, quantity, product.getStock());
        }
        product.setStock(product.getStock() - quantity);
        log.info("扣减库存: productId={}, quantity={}, remaining={}", productId, quantity, product.getStock());
    }

    public void delete(String id) {
        if (products.remove(id) == null) throw new ResourceNotFoundException("商品不存在: " + id);
        log.info("删除商品: id={}", id);
    }
}
