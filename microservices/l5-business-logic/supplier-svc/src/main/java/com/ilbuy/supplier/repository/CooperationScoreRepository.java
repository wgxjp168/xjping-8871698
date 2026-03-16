package com.ilbuy.supplier.repository;

import com.ilbuy.supplier.model.entity.CooperationScore;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;

@Repository
public interface CooperationScoreRepository extends JpaRepository<CooperationScore, Long> {

    Page<CooperationScore> findBySupplierId(Long supplierId, Pageable pageable);

    @Query("SELECT AVG(c.overallScore) FROM CooperationScore c WHERE c.supplierId = :supplierId")
    BigDecimal calculateAverageScoreBySupplierId(@Param("supplierId") Long supplierId);

    long countBySupplierId(Long supplierId);
}
