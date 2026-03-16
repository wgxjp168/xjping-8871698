package com.ilbuy.recommend.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ilbuy.recommend.dto.B2BRecommendDTO;
import com.ilbuy.recommend.dto.B2BTrackEventRequest;
import com.ilbuy.recommend.dto.HomepageRecommendDTO;
import com.ilbuy.recommend.dto.RecommendItemDTO;
import com.ilbuy.recommend.dto.TrackEventRequest;
import com.ilbuy.recommend.dto.UserProfileDTO;
import com.ilbuy.recommend.engine.CollaborativeFilteringEngine;
import com.ilbuy.recommend.engine.ContentBasedEngine;
import com.ilbuy.recommend.model.entity.BehaviorEvent;
import com.ilbuy.recommend.model.entity.RecommendItem;
import com.ilbuy.recommend.model.entity.UserProfile;
import com.ilbuy.recommend.model.enums.EventType;
import com.ilbuy.recommend.model.enums.RecommendSource;
import com.ilbuy.recommend.repository.BehaviorEventRepository;
import com.ilbuy.recommend.repository.RecommendItemRepository;
import com.ilbuy.recommend.repository.UserProfileRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class RecommendService {

    private static final String CACHE_HOMEPAGE_PREFIX    = "recommend:homepage:";
    private static final String CACHE_SIMILAR_PREFIX     = "recommend:similar:";
    private static final String CACHE_B2B_HOMEPAGE_PREFIX = "recommend:b2b:";

    private final UserProfileRepository       userProfileRepository;
    private final BehaviorEventRepository     behaviorEventRepository;
    private final RecommendItemRepository     recommendItemRepository;
    private final CollaborativeFilteringEngine cfEngine;
    private final ContentBasedEngine          contentEngine;
    private final RedisTemplate<String, Object> redisTemplate;
    private final ObjectMapper                objectMapper;

    @Value("${recommend.cache.homepage-ttl-minutes:30}")
    private long homepageTtlMinutes;

    @Value("${recommend.cache.similar-ttl-minutes:10}")
    private long similarTtlMinutes;

    @Value("${recommend.engine.hot-limit:10}")
    private int hotLimit;

    @Value("${recommend.engine.new-limit:10}")
    private int newLimit;

    @Value("${recommend.engine.foryou-limit:20}")
    private int forYouLimit;

    // -------------------------------------------------------------------------
    // Homepage recommendations
    // -------------------------------------------------------------------------

    @Transactional(readOnly = true)
    public HomepageRecommendDTO getHomepageRecommendations(Long userId) {
        String cacheKey = CACHE_HOMEPAGE_PREFIX + userId;

        // Check Redis cache
        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof HomepageRecommendDTO dto) {
            log.debug("Cache hit for homepage recommendations, userId={}", userId);
            return dto;
        }

        log.debug("Cache miss for homepage recommendations, userId={}", userId);

        // HOT items
        List<RecommendItem> hotItems = recommendItemRepository
            .findBySourceOrderByScoreDesc(RecommendSource.HOT, PageRequest.of(0, hotLimit));

        // NEW items
        List<RecommendItem> newItems = recommendItemRepository
            .findBySourceOrderByScoreDesc(RecommendSource.NEW, PageRequest.of(0, newLimit));

        // FOR_YOU: CF + content-based, merged and deduped
        List<RecommendItem> cfItems      = cfEngine.recommend(userId, forYouLimit);
        List<RecommendItem> contentItems = contentEngine.recommend(userId, forYouLimit);

        List<RecommendItem> forYouItems = mergeAndDedupe(cfItems, contentItems, forYouLimit);

        HomepageRecommendDTO result = HomepageRecommendDTO.builder()
            .hot(toDto(hotItems))
            .forYou(toDto(forYouItems))
            .newArrivals(toDto(newItems))
            .build();

        // Cache result
        redisTemplate.opsForValue().set(cacheKey, result, homepageTtlMinutes, TimeUnit.MINUTES);

        return result;
    }

    // -------------------------------------------------------------------------
    // Track behavior event
    // -------------------------------------------------------------------------

    @Transactional
    public void trackEvent(Long userId, TrackEventRequest request) {
        BehaviorEvent event = BehaviorEvent.builder()
            .userId(userId)
            .eventType(request.getEventType())
            .productId(request.getProductId())
            .canonicalId(request.getCanonicalId())
            .category(request.getCategory())
            .platform(request.getPlatform())
            .keyword(request.getKeyword())
            .build();

        behaviorEventRepository.save(event);
        log.debug("Tracked event: userId={} eventType={}", userId, request.getEventType());

        // Async update user profile
        updateUserProfileAsync(userId, request);
    }

    @Async
    public void updateUserProfileAsync(Long userId, TrackEventRequest request) {
        try {
            UserProfile profile = userProfileRepository.findByUserId(userId)
                .orElseGet(() -> UserProfile.builder()
                    .userId(userId)
                    .totalViews(0L)
                    .totalOrders(0L)
                    .build());

            EventType eventType = request.getEventType();

            if (eventType == EventType.VIEW || eventType == EventType.CLICK) {
                profile.setTotalViews(profile.getTotalViews() + 1);
            }
            if (eventType == EventType.ORDER) {
                profile.setTotalOrders(profile.getTotalOrders() + 1);
            }

            profile.setLastActiveAt(LocalDateTime.now());

            // Update preferred categories
            if (request.getCategory() != null && !request.getCategory().isBlank()) {
                String updatedCategories = addToJsonList(
                    profile.getPreferredCategories(), request.getCategory());
                profile.setPreferredCategories(updatedCategories);
            }

            // Update preferred platforms
            if (request.getPlatform() != null && !request.getPlatform().isBlank()) {
                String updatedPlatforms = addToJsonList(
                    profile.getPreferredPlatforms(), request.getPlatform());
                profile.setPreferredPlatforms(updatedPlatforms);
            }

            userProfileRepository.save(profile);

            // Invalidate homepage cache so next request rebuilds recommendations
            redisTemplate.delete(CACHE_HOMEPAGE_PREFIX + userId);

            log.debug("Updated user profile asynchronously for userId={}", userId);
        } catch (Exception e) {
            log.error("Failed to update user profile for userId={}: {}", userId, e.getMessage(), e);
        }
    }

    // -------------------------------------------------------------------------
    // Similar products
    // -------------------------------------------------------------------------

    @Transactional(readOnly = true)
    public List<RecommendItemDTO> getSimilarProducts(Long canonicalId) {
        String cacheKey = CACHE_SIMILAR_PREFIX + canonicalId;

        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof List<?> list) {
            log.debug("Cache hit for similar products, canonicalId={}", canonicalId);
            //noinspection unchecked
            return (List<RecommendItemDTO>) list;
        }

        log.debug("Cache miss for similar products, canonicalId={}", canonicalId);

        // Mock: return top 10 HOT items as similar products
        List<RecommendItem> hotItems = recommendItemRepository
            .findBySourceOrderByScoreDesc(RecommendSource.HOT, PageRequest.of(0, 10));

        List<RecommendItemDTO> result = toDto(hotItems);
        redisTemplate.opsForValue().set(cacheKey, result, similarTtlMinutes, TimeUnit.MINUTES);

        return result;
    }

    // -------------------------------------------------------------------------
    // Get user profile
    // -------------------------------------------------------------------------

    @Transactional(readOnly = true)
    public UserProfileDTO getUserProfile(Long userId) {
        UserProfile profile = userProfileRepository.findByUserId(userId)
            .orElseGet(() -> UserProfile.builder()
                .userId(userId)
                .totalViews(0L)
                .totalOrders(0L)
                .build());

        return UserProfileDTO.builder()
            .userId(profile.getUserId())
            .preferredCategories(profile.getPreferredCategories())
            .preferredPlatforms(profile.getPreferredPlatforms())
            .priceRangeMin(profile.getPriceRangeMin())
            .priceRangeMax(profile.getPriceRangeMax())
            .totalViews(profile.getTotalViews())
            .totalOrders(profile.getTotalOrders())
            .lastActiveAt(profile.getLastActiveAt())
            .updatedAt(profile.getUpdatedAt())
            .build();
    }

    // -------------------------------------------------------------------------
    // B2B Procurement Recommendations
    // -------------------------------------------------------------------------

    /**
     * Returns B2B procurement homepage recommendations for the authenticated buyer.
     * B2B scene: surfaces frequently purchased items, category-matched products,
     * new supplier stock, and recommended suppliers — all tailored to procurement history.
     * Cache: "recommend:b2b:{userId}" TTL=1h (B2B recommendations change less frequently than B2C).
     */
    @Transactional(readOnly = true)
    public B2BRecommendDTO getB2BHomepageRecommendations(Long userId) {
        String cacheKey = CACHE_B2B_HOMEPAGE_PREFIX + userId;

        Object cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached instanceof B2BRecommendDTO dto) {
            log.debug("Cache hit for B2B homepage recommendations, userId={}", userId);
            return dto;
        }

        log.debug("Cache miss for B2B homepage recommendations, userId={}", userId);

        // frequentlyPurchased: CF-sourced items where the user has the most ORDER events
        List<RecommendItem> cfItems = cfEngine.recommend(userId, forYouLimit);
        List<RecommendItemDTO> frequentlyPurchased = toDto(cfItems);

        // categoryBased: content-based items matching user's most-ordered categories
        List<RecommendItem> contentItems = contentEngine.recommend(userId, forYouLimit);
        List<RecommendItemDTO> categoryBased = toDto(contentItems);

        // newSupplierProducts: NEW-sourced items from the recommendation pool
        List<RecommendItem> newItems = recommendItemRepository
            .findBySourceOrderByScoreDesc(RecommendSource.NEW, PageRequest.of(0, newLimit));
        List<RecommendItemDTO> newSupplierProducts = toDto(newItems);

        // recommendedSuppliers: mock list (production would derive from category match)
        List<String> recommendedSuppliers = recommendSuppliers(userId);

        B2BRecommendDTO result = B2BRecommendDTO.builder()
            .frequentlyPurchased(frequentlyPurchased)
            .categoryBased(categoryBased)
            .newSupplierProducts(newSupplierProducts)
            .recommendedSuppliers(recommendedSuppliers)
            .build();

        // B2B recommendations are cached for 1 hour — procurement patterns change less frequently than B2C browsing
        redisTemplate.opsForValue().set(cacheKey, result, 1, TimeUnit.HOURS);

        return result;
    }

    /**
     * Tracks a B2B procurement behavior event.
     * B2B scene: captures procurement-specific actions (RFQ, bulk order, contract signing)
     * that differ fundamentally from B2C browsing events.
     * Maps B2B event types to the nearest generic EventType for storage.
     */
    @Transactional
    public void trackB2BEvent(Long userId, B2BTrackEventRequest req) {
        // Map B2B-specific event types to the nearest generic EventType
        EventType mappedType;
        switch (req.getEventType()) {
            case "BULK_ORDER":
            case "CONTRACT_SIGN":
                mappedType = EventType.ORDER;
                break;
            case "RFQ_SUBMIT":
                mappedType = EventType.ORDER;
                break;
            case "PROCUREMENT_VIEW":
            default:
                mappedType = EventType.VIEW;
                break;
        }

        BehaviorEvent event = BehaviorEvent.builder()
            .userId(userId)
            .eventType(mappedType)
            .category(req.getCategory())
            .build();

        behaviorEventRepository.save(event);
        log.info("B2B event tracked: userId={} type={} supplierNo={}",
            userId, req.getEventType(), req.getSupplierNo());

        // Invalidate B2B homepage cache so next request rebuilds recommendations
        redisTemplate.delete(CACHE_B2B_HOMEPAGE_PREFIX + userId);
    }

    /**
     * Recommends suppliers based on the user's ORDER behavior history.
     * B2B scene: helps buyers discover and diversify their supplier base
     * by matching against categories they frequently procure.
     * Returns up to 5 supplier numbers.
     */
    @Transactional(readOnly = true)
    public List<String> recommendSuppliers(Long userId) {
        // Derive suppliers from the user's ORDER events and their categories
        List<BehaviorEvent> orderEvents = behaviorEventRepository
            .findByUserIdAndEventTypeOrderByCreatedAtDesc(userId, EventType.ORDER,
                PageRequest.of(0, 20));

        List<String> suppliers = orderEvents.stream()
            .map(BehaviorEvent::getCategory)
            .filter(Objects::nonNull)
            .distinct()
            .map(category -> "SUP" + (Math.abs(category.hashCode()) % 1000))
            .limit(5)
            .collect(Collectors.toList());

        // Fall back to well-known mock suppliers when the user has no procurement history
        if (suppliers.isEmpty()) {
            suppliers = Arrays.asList("SUP001", "SUP002");
        }

        return suppliers;
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    private List<RecommendItem> mergeAndDedupe(List<RecommendItem> primary,
                                                List<RecommendItem> secondary,
                                                int limit) {
        Map<Long, RecommendItem> deduped = new LinkedHashMap<>();
        for (RecommendItem item : primary) {
            if (item.getCanonicalId() != null) {
                deduped.put(item.getCanonicalId(), item);
            } else {
                deduped.put(item.getId(), item);
            }
        }
        for (RecommendItem item : secondary) {
            Long key = item.getCanonicalId() != null ? item.getCanonicalId() : item.getId();
            deduped.putIfAbsent(key, item);
        }
        return deduped.values().stream()
            .limit(limit)
            .collect(Collectors.toList());
    }

    private List<RecommendItemDTO> toDto(List<RecommendItem> items) {
        return items.stream()
            .map(item -> RecommendItemDTO.builder()
                .id(item.getId())
                .canonicalId(item.getCanonicalId())
                .platform(item.getPlatform())
                .productTitle(item.getProductTitle())
                .imageUrl(item.getImageUrl())
                .currentPrice(item.getCurrentPrice())
                .score(item.getScore())
                .source(item.getSource())
                .createdAt(item.getCreatedAt())
                .expiresAt(item.getExpiresAt())
                .build())
            .collect(Collectors.toList());
    }

    /**
     * Adds a value to a JSON array string. Keeps the list to at most 50 unique entries.
     */
    private String addToJsonList(String jsonList, String value) {
        try {
            List<String> list = new ArrayList<>();
            if (jsonList != null && !jsonList.isBlank()) {
                list = objectMapper.readValue(jsonList, new TypeReference<List<String>>() {});
            }
            if (!list.contains(value)) {
                list.add(0, value);
                if (list.size() > 50) {
                    list = list.subList(0, 50);
                }
            }
            return objectMapper.writeValueAsString(list);
        } catch (JsonProcessingException e) {
            log.warn("Failed to update JSON list: {}", e.getMessage());
            return jsonList;
        }
    }
}
