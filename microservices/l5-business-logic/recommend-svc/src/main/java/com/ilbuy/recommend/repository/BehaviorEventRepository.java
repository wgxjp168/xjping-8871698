package com.ilbuy.recommend.repository;

import com.ilbuy.recommend.model.entity.BehaviorEvent;
import com.ilbuy.recommend.model.enums.EventType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface BehaviorEventRepository extends JpaRepository<BehaviorEvent, Long> {

    /**
     * Find the most recent VIEW events for a user (for content-based filtering).
     */
    List<BehaviorEvent> findByUserIdAndEventTypeOrderByCreatedAtDesc(Long userId, EventType eventType);

    /**
     * Find all ORDER events for a given user.
     */
    List<BehaviorEvent> findByUserIdAndEventType(Long userId, EventType eventType);

    /**
     * Find distinct categories from ORDER events for a user.
     */
    @Query("SELECT DISTINCT b.category FROM BehaviorEvent b WHERE b.userId = :userId AND b.eventType = :eventType AND b.category IS NOT NULL")
    List<String> findDistinctCategoriesByUserIdAndEventType(@Param("userId") Long userId,
                                                            @Param("eventType") EventType eventType);

    /**
     * Find distinct canonical IDs ordered by a user.
     */
    @Query("SELECT DISTINCT b.canonicalId FROM BehaviorEvent b WHERE b.userId = :userId AND b.eventType = 'ORDER' AND b.canonicalId IS NOT NULL")
    List<Long> findOrderedCanonicalIdsByUserId(@Param("userId") Long userId);

    /**
     * Find users who ordered products in the given categories (for CF).
     */
    @Query("SELECT b.userId FROM BehaviorEvent b WHERE b.eventType = 'ORDER' AND b.category IN :categories AND b.userId != :excludeUserId GROUP BY b.userId ORDER BY COUNT(b.id) DESC")
    List<Long> findTopUsersByOrderCategories(@Param("categories") List<String> categories,
                                             @Param("excludeUserId") Long excludeUserId);
}
