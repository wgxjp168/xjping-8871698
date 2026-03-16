package com.ilbuy.recommend.api;

import com.ilbuy.recommend.dto.HomepageRecommendDTO;
import com.ilbuy.recommend.dto.RecommendItemDTO;
import com.ilbuy.recommend.dto.TrackEventRequest;
import com.ilbuy.recommend.dto.UserProfileDTO;
import com.ilbuy.recommend.service.RecommendService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/recommendations")
@RequiredArgsConstructor
@Slf4j
public class RecommendController {

    private final RecommendService recommendService;

    /**
     * GET /api/v1/recommendations/homepage
     * Returns personalised homepage recommendations for the authenticated user.
     * Requires auth.
     */
    @GetMapping("/homepage")
    public ResponseEntity<HomepageRecommendDTO> getHomepageRecommendations(
        @AuthenticationPrincipal Long userId) {

        log.debug("GET /homepage for userId={}", userId);
        HomepageRecommendDTO dto = recommendService.getHomepageRecommendations(userId);
        return ResponseEntity.ok(dto);
    }

    /**
     * GET /api/v1/recommendations/similar/{canonicalId}
     * Returns similar products for the given canonical product. Public endpoint.
     */
    @GetMapping("/similar/{canonicalId}")
    public ResponseEntity<List<RecommendItemDTO>> getSimilarProducts(
        @PathVariable Long canonicalId) {

        log.debug("GET /similar/{}", canonicalId);
        List<RecommendItemDTO> items = recommendService.getSimilarProducts(canonicalId);
        return ResponseEntity.ok(items);
    }

    /**
     * POST /api/v1/recommendations/track
     * Tracks a user behavior event. Requires auth.
     */
    @PostMapping("/track")
    public ResponseEntity<Void> trackEvent(
        @AuthenticationPrincipal Long userId,
        @Valid @RequestBody TrackEventRequest request) {

        log.debug("POST /track for userId={} eventType={}", userId, request.getEventType());
        recommendService.trackEvent(userId, request);
        return ResponseEntity.accepted().build();
    }

    /**
     * GET /api/v1/recommendations/profile
     * Returns the current user's preference profile. Requires auth.
     */
    @GetMapping("/profile")
    public ResponseEntity<UserProfileDTO> getUserProfile(
        @AuthenticationPrincipal Long userId) {

        log.debug("GET /profile for userId={}", userId);
        UserProfileDTO profile = recommendService.getUserProfile(userId);
        return ResponseEntity.ok(profile);
    }
}
