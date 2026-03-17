package com.ilbuy.gateway.repository;

import com.ilbuy.gateway.domain.ProfitSharingRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface ProfitSharingRepository extends JpaRepository<ProfitSharingRecord, Long> {
    Optional<ProfitSharingRecord> findByOrderNo(String orderNo);
    List<ProfitSharingRecord> findByPaymentNo(String paymentNo);
    Optional<ProfitSharingRecord> findByChannelSharingId(String channelSharingId);
}
