package com.ilbuy.recommend.repository;

import com.ilbuy.recommend.model.entity.RecommendItem;
import com.ilbuy.recommend.model.enums.RecommendSource;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RecommendItemRepository extends JpaRepository<RecommendItem, Long> {

    /**
     * Find global items by source (HOT, NEW), ordered by score descending.
     */
    List<RecommendItem> findBySourceOrderByScoreDesc(RecommendSource source, Pageable pageable);

    /**
     * Find items by source and category list (for content-based recommendations).
     */
    @Query("SELECT r FROM RecommendItem r WHERE r.source IN :sources ORDER BY r.score DESC")
    List<RecommendItem> findBySourceIn(@Param("sources") List<RecommendSource> sources, Pageable pageable);

    /**
     * Find items by canonical IDs.
     */
    @Query("SELECT r FROM RecommendItem r WHERE r.canonicalId IN :canonicalIds ORDER BY r.score DESC")
    List<RecommendItem> findByCanonicalIdIn(@Param("canonicalIds") List<Long> canonicalIds, Pageable pageable);

    /**
     * Find top HOT items as fallback.
     */
    @Query("SELECT r FROM RecommendItem r WHERE r.source = 'HOT' ORDER BY r.score DESC")
    List<RecommendItem> findTopHotItems(Pageable pageable);
}
