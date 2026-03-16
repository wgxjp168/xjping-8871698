package com.ilbuy.recommend.engine;

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

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Simple collaborative filtering engine.
 *
 * Algorithm:
 *  1. Find the categories the target user has ordered.
 *  2. Find the top-N other users who have ordered most in those categories.
 *  3. Gather canonical IDs those similar users ordered that the target user has NOT ordered.
 *  4. Return RecommendItems for those canonical IDs.
 *  5. If insufficient data, fall back to HOT items.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class CollaborativeFilteringEngine {

    private final BehaviorEventRepository behaviorEventRepository;
    private final RecommendItemRepository recommendItemRepository;

    @Value("${recommend.engine.cf-top-users:5}")
    private int cfTopUsers;

    @Value("${recommend.engine.cf-limit:20}")
    private int cfLimit;

    public List<RecommendItem> recommend(Long userId, int limit) {
        log.debug("CF engine: computing recommendations for userId={}", userId);

        // Step 1: find categories the user has ordered
        List<String> userCategories = behaviorEventRepository
            .findDistinctCategoriesByUserIdAndEventType(userId, EventType.ORDER);

        if (userCategories.isEmpty()) {
            log.debug("CF engine: no order history for userId={}, falling back to HOT", userId);
            return fallbackToHot(limit);
        }

        // Step 2: find similar users (top-N by order count in same categories)
        List<Long> similarUserIds = behaviorEventRepository
            .findTopUsersByOrderCategories(userCategories, userId)
            .stream()
            .limit(cfTopUsers)
            .collect(Collectors.toList());

        if (similarUserIds.isEmpty()) {
            log.debug("CF engine: no similar users found for userId={}, falling back to HOT", userId);
            return fallbackToHot(limit);
        }

        // Step 3: collect canonical IDs that target user has already ordered
        Set<Long> alreadyOrderedCanonicalIds = behaviorEventRepository
            .findOrderedCanonicalIdsByUserId(userId)
            .stream()
            .collect(Collectors.toSet());

        // Step 4: collect canonical IDs ordered by similar users but not by target user
        List<Long> candidateCanonicalIds = new ArrayList<>();
        for (Long similarUserId : similarUserIds) {
            List<Long> similarUserOrders = behaviorEventRepository
                .findOrderedCanonicalIdsByUserId(similarUserId);
            for (Long cid : similarUserOrders) {
                if (!alreadyOrderedCanonicalIds.contains(cid) && !candidateCanonicalIds.contains(cid)) {
                    candidateCanonicalIds.add(cid);
                }
            }
            if (candidateCanonicalIds.size() >= limit * 2) {
                break;
            }
        }

        if (candidateCanonicalIds.isEmpty()) {
            log.debug("CF engine: no candidate items for userId={}, falling back to HOT", userId);
            return fallbackToHot(limit);
        }

        // Step 5: fetch RecommendItems for candidate canonical IDs
        List<RecommendItem> items = recommendItemRepository
            .findByCanonicalIdIn(candidateCanonicalIds, PageRequest.of(0, limit));

        if (items.size() < limit) {
            // supplement with HOT items
            List<RecommendItem> hotItems = fallbackToHot(limit - items.size());
            Set<Long> existingIds = items.stream()
                .map(RecommendItem::getCanonicalId)
                .collect(Collectors.toSet());
            hotItems.stream()
                .filter(h -> !existingIds.contains(h.getCanonicalId()))
                .forEach(items::add);
        }

        return items.stream().limit(limit).collect(Collectors.toList());
    }

    private List<RecommendItem> fallbackToHot(int limit) {
        return recommendItemRepository.findTopHotItems(PageRequest.of(0, limit));
    }
}
