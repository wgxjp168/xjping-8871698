package com.ilbuy.bmonetize.repository;

import com.ilbuy.bmonetize.domain.BMonetizeOrder;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.*;

public interface BMonetizeOrderRepository extends JpaRepository<BMonetizeOrder, Long> {
    Optional<BMonetizeOrder> findByOrderNo(String orderNo);
    Optional<BMonetizeOrder> findByPaymentNo(String paymentNo);
    List<BMonetizeOrder> findByCorpIdOrderByCreatedAtDesc(Long corpId);
}
