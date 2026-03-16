package com.ilbuy.recommend.api;

import com.ilbuy.recommend.dto.B2BRecommendDTO;
import com.ilbuy.recommend.dto.B2BTrackEventRequest;
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

    // -------------------------------------------------------------------------
    // B2B Procurement Recommendation endpoints
    // -------------------------------------------------------------------------

    /**
     * GET /api/v1/recommendations/b2b/homepage
     * Returns B2B procurement homepage recommendations for the authenticated buyer.
     * B2B scene: personalised procurement suggestions — frequently purchased products,
     * category-matched items, new supplier stock, and recommended suppliers.
     * Requires auth.
     */
    @GetMapping("/b2b/homepage")
    public ResponseEntity<B2BRecommendDTO> getB2BHomepageRecommendations(
        @AuthenticationPrincipal Long userId) {

        log.debug("GET /b2b/homepage for userId={}", userId);
        B2BRecommendDTO dto = recommendService.getB2BHomepageRecommendations(userId);
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/recommendations/b2b/track
     * Tracks a B2B procurement behavior event. Requires auth.
     * B2B scene: captures procurement-specific actions (PROCUREMENT_VIEW, RFQ_SUBMIT,
     * BULK_ORDER, CONTRACT_SIGN) that are distinct from B2C browsing events.
     */
    @PostMapping("/b2b/track")
    public ResponseEntity<Void> trackB2BEvent(
        @AuthenticationPrincipal Long userId,
        @Valid @RequestBody B2BTrackEventRequest request) {

        log.debug("POST /b2b/track for userId={} eventType={}", userId, request.getEventType());
        recommendService.trackB2BEvent(userId, request);
        return ResponseEntity.accepted().build();
    }

    /**
     * GET /api/v1/recommendations/b2b/suppliers
     * Recommends suppliers based on the authenticated user's procurement categories. Requires auth.
     * B2B scene: helps buyers discover and diversify their supplier base by surfacing
     * suppliers that match their historically procured categories.
     */
    @GetMapping("/b2b/suppliers")
    public ResponseEntity<List<String>> recommendSuppliers(
        @AuthenticationPrincipal Long userId) {

        log.debug("GET /b2b/suppliers for userId={}", userId);
        List<String> suppliers = recommendService.recommendSuppliers(userId);
        return ResponseEntity.ok(suppliers);
    }
}
