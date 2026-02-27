package com.ilbuy.data.service;

import com.ilbuy.data.entity.OrderEntity;
import com.ilbuy.data.repository.OrderRepository;
import org.springframework.stereotype.Service;
import java.util.List;

@Service
public class DataOrderService {

    private final OrderRepository repo;

    public DataOrderService(OrderRepository repo) { this.repo = repo; }

    public List<OrderEntity> findAll() { return repo.findAll(); }
    public OrderEntity findById(String id) { return repo.findById(id).orElse(null); }
    public List<OrderEntity> findByUserId(String userId) { return repo.findByUserId(userId); }
    public OrderEntity save(OrderEntity o) { return repo.save(o); }
    public List<OrderEntity> findByStatus(String status) { return repo.findByStatus(status); }
}
