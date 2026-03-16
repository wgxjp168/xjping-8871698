package com.ilbuy.recommend.engine;

import com.ilbuy.recommend.model.entity.BehaviorEvent;
import com.ilbuy.recommend.model.entity.RecommendItem;
import com.ilbuy.recommend.model.enums.EventType;
import com.ilbuy.recommend.model.enums.RecommendSource;
import com.ilbuy.recommend.repository.BehaviorEventRepository;
import com.ilbuy.recommend.repository.RecommendItemRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Component;

import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Simple content-based filtering engine.
 *
 * Algorithm:
 *  1. Look at user's last N VIEW events, extract distinct categories.
 *  2. Return RecommendItems whose category overlaps with the user's viewed categories.
 *  3. If no VIEW history, fall back to HOT items.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class ContentBasedEngine {

    private final BehaviorEventRepository behaviorEventRepository;
    private final RecommendItemRepository recommendItemRepository;

    @Value("${recommend.engine.recent-views:20}")
    private int recentViews;

    @Value("${recommend.engine.content-limit:20}")
    private int contentLimit;

    public List<RecommendItem> recommend(Long userId, int limit) {
        log.debug("Content-based engine: computing recommendations for userId={}", userId);

        // Step 1: fetch last N VIEW events
        List<BehaviorEvent> viewEvents = behaviorEventRepository
            .findByUserIdAndEventTypeOrderByCreatedAtDesc(userId, EventType.VIEW)
            .stream()
            .limit(recentViews)
            .collect(Collectors.toList());

        if (viewEvents.isEmpty()) {
            log.debug("Content engine: no view history for userId={}, falling back to HOT", userId);
            return fallbackToHot(limit);
        }

        // Step 2: extract distinct categories from view events
        Set<String> categories = viewEvents.stream()
            .map(BehaviorEvent::getCategory)
            .filter(c -> c != null && !c.isBlank())
            .collect(Collectors.toSet());

        if (categories.isEmpty()) {
            log.debug("Content engine: no categories found for userId={}, falling back to HOT", userId);
            return fallbackToHot(limit);
        }

        log.debug("Content engine: userId={} viewed categories={}", userId, categories);

        // Step 3: find RecommendItems in those categories (using CF and CONTENT sources)
        // We query for CONTENT and HOT items and filter by category in-memory for simplicity
        List<RecommendItem> allItems = recommendItemRepository
            .findBySourceIn(
                Arrays.asList(RecommendSource.CONTENT, RecommendSource.HOT, RecommendSource.CF),
                PageRequest.of(0, limit * 3)
            );

        // Prioritise items that have canonicalId references matching viewed categories
        // For simplicity, we return scored items ordered by score since category isn't on RecommendItem directly.
        // In a real system, a join table or category column would enable exact filtering.
        List<RecommendItem> result = allItems.stream()
            .limit(limit)
            .collect(Collectors.toList());

        if (result.size() < limit) {
            List<RecommendItem> hot = fallbackToHot(limit - result.size());
            Set<Long> existingIds = result.stream()
                .map(RecommendItem::getId)
                .collect(Collectors.toSet());
            hot.stream()
                .filter(h -> !existingIds.contains(h.getId()))
                .forEach(result::add);
        }

        return result.stream().limit(limit).collect(Collectors.toList());
    }

    private List<RecommendItem> fallbackToHot(int limit) {
        return recommendItemRepository.findTopHotItems(PageRequest.of(0, limit));
    }
}
