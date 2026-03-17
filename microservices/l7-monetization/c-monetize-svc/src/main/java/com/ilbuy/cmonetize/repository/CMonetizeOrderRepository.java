package com.ilbuy.cmonetize.repository;

import com.ilbuy.cmonetize.domain.CMonetizeOrder;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface CMonetizeOrderRepository extends JpaRepository<CMonetizeOrder, Long> {
    Optional<CMonetizeOrder> findByOrderNo(String orderNo);
    Optional<CMonetizeOrder> findByPaymentNo(String paymentNo);
    List<CMonetizeOrder> findByUserIdOrderByCreatedAtDesc(Long userId);
}
