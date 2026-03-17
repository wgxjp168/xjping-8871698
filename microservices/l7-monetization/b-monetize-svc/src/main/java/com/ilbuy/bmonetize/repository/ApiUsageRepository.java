package com.ilbuy.bmonetize.repository;

import com.ilbuy.bmonetize.domain.ApiUsageRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;

public interface ApiUsageRepository extends JpaRepository<ApiUsageRecord, Long> {
    List<ApiUsageRecord> findByCorpIdAndBillingPeriod(Long corpId, String billingPeriod);

    @Query("SELECT SUM(r.callCount) FROM ApiUsageRecord r WHERE r.corpId = :corpId AND r.billingPeriod = :period")
    Long sumCallsByCorpAndPeriod(Long corpId, String period);
}
