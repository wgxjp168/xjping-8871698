package com.ilbuy.billing.repository;

import com.ilbuy.billing.domain.RefundRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RefundRecordRepository extends JpaRepository<RefundRecord, Long> {

    Optional<RefundRecord> findByRefundNo(String refundNo);

    List<RefundRecord> findByOriginalOrderNo(String originalOrderNo);

    Optional<RefundRecord> findByPaymentNo(String paymentNo);
}
