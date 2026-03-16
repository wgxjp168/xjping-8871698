package com.ilbuy.price.repository;

import com.ilbuy.price.model.entity.PriceAlert;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface PriceAlertRepository extends JpaRepository<PriceAlert, Long> {

    /**
     * Find all alerts for a given user.
     */
    List<PriceAlert> findByUserIdOrderByCreatedAtDesc(Long userId);

    /**
     * Find all untriggered price alerts (for the scheduler to check).
     */
    List<PriceAlert> findByTriggeredFalse();

    /**
     * Find a specific alert by ID and userId (ownership check).
     */
    Optional<PriceAlert> findByIdAndUserId(Long id, Long userId);
}
