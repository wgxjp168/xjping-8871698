package com.ilbuy.data.repository;

import com.ilbuy.data.entity.OrderEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface OrderRepository extends JpaRepository<OrderEntity, String> {

    List<OrderEntity> findByUserId(String userId);

    List<OrderEntity> findByStatus(String status);

    List<OrderEntity> findByUserIdAndStatus(String userId, String status);

    List<OrderEntity> findByCreatedAtBetween(LocalDateTime start, LocalDateTime end);
}
