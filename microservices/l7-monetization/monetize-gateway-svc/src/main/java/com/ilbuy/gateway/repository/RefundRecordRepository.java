package com.ilbuy.gateway.repository;

import com.ilbuy.gateway.domain.RefundRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface RefundRecordRepository extends JpaRepository<RefundRecord, Long> {
    Optional<RefundRecord> findByRefundNo(String refundNo);
    List<RefundRecord> findByPaymentNo(String paymentNo);
}
