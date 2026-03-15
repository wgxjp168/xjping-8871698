package com.ilbuy.datasvc.repository.mysql;

import com.ilbuy.datasvc.model.entity.PriceHistory;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PriceHistoryRepository extends JpaRepository<PriceHistory, Long> {

    List<PriceHistory> findByCanonicalIdOrderByRecordedAtDesc(String canonicalId, Pageable pageable);

    long countByCanonicalId(String canonicalId);
}
