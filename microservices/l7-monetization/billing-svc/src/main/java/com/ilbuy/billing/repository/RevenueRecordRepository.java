package com.ilbuy.billing.repository;

import com.ilbuy.billing.domain.RevenueRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface RevenueRecordRepository extends JpaRepository<RevenueRecord, Long> {

    Optional<RevenueRecord> findByPeriodAndOrderType(String period, String orderType);

    List<RevenueRecord> findByPeriod(String period);
}
