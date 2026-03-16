package com.ilbuy.order.repository;

import com.ilbuy.order.model.entity.Order;
import com.ilbuy.order.model.enums.OrderStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.Instant;
import java.util.Optional;

public interface OrderRepository extends JpaRepository<Order, Long> {

    Optional<Order> findByOrderNo(String orderNo);

    Page<Order> findByUserId(Long userId, Pageable pageable);

    Page<Order> findByUserIdAndStatus(Long userId, OrderStatus status, Pageable pageable);

    Page<Order> findByStatus(OrderStatus status, Pageable pageable);

    @Query("SELECT o FROM Order o WHERE o.userId = :uid AND o.createdAt BETWEEN :from AND :to")
    Page<Order> findByUserIdAndDateRange(
        @Param("uid")  Long userId,
        @Param("from") Instant from,
        @Param("to")   Instant to,
        Pageable pageable
    );

    long countByStatus(OrderStatus status);
}
