package com.ilbuy.gateway.repository;

import com.ilbuy.gateway.domain.PaymentOrder;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;
import java.util.List;

public interface PaymentOrderRepository extends JpaRepository<PaymentOrder, Long> {
    Optional<PaymentOrder> findByPaymentNo(String paymentNo);
    Optional<PaymentOrder> findByBizOrderNo(String bizOrderNo);
    List<PaymentOrder> findByUserIdOrderByCreatedAtDesc(Long userId);
    boolean existsByBizOrderNo(String bizOrderNo);
}
