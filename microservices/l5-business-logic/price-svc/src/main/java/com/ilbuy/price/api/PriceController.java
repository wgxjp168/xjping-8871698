package com.ilbuy.price.api;

import com.ilbuy.price.dto.*;
import com.ilbuy.price.service.PriceService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/prices")
@RequiredArgsConstructor
@Slf4j
public class PriceController {

    private final PriceService priceService;

    /**
     * GET /api/v1/prices/{canonicalId}/history
     * Returns price history for a product. Public endpoint.
     *
     * @param canonicalId canonical product ID
     * @param platform    optional platform filter
     * @param days        number of days to look back (default 30)
     */
    @GetMapping("/{canonicalId}/history")
    public ResponseEntity<PriceHistoryDTO> getPriceHistory(
        @PathVariable Long canonicalId,
        @RequestParam(required = false) String platform,
        @RequestParam(defaultValue = "30") int days) {

        log.debug("GET /prices/{}/history platform={} days={}", canonicalId, platform, days);
        PriceHistoryDTO dto = priceService.getPriceHistory(canonicalId, platform, days);
        return ResponseEntity.ok(dto);
    }

    /**
     * GET /api/v1/prices/{canonicalId}/trend
     * Returns price trend chart data for a product. Public endpoint.
     *
     * @param canonicalId canonical product ID
     * @param platform    optional platform filter
     * @param granularity trend granularity: DAILY (default), WEEKLY, MONTHLY
     * @param days        number of days to look back (default 90)
     */
    @GetMapping("/{canonicalId}/trend")
    public ResponseEntity<PriceTrendDTO> getPriceTrend(
        @PathVariable Long canonicalId,
        @RequestParam(required = false) String platform,
        @RequestParam(defaultValue = "DAILY") String granularity,
        @RequestParam(defaultValue = "90") int days) {

        log.debug("GET /prices/{}/trend platform={} granularity={} days={}",
            canonicalId, platform, granularity, days);
        PriceTrendDTO dto = priceService.getPriceTrend(canonicalId, platform, granularity, days);
        return ResponseEntity.ok(dto);
    }

    /**
     * GET /api/v1/prices/{canonicalId}/compare
     * Returns cross-platform price comparison sorted by price ASC. Public endpoint.
     *
     * @param canonicalId canonical product ID
     */
    @GetMapping("/{canonicalId}/compare")
    public ResponseEntity<CrossPlatformPriceDTO> getCrossPlatformComparison(
        @PathVariable Long canonicalId) {

        log.debug("GET /prices/{}/compare", canonicalId);
        CrossPlatformPriceDTO dto = priceService.getCrossPlatformComparison(canonicalId);
        return ResponseEntity.ok(dto);
    }

    /**
     * POST /api/v1/prices/alerts
     * Creates a price drop alert for the authenticated user.
     */
    @PostMapping("/alerts")
    public ResponseEntity<PriceAlertDTO> createAlert(
        @AuthenticationPrincipal Long userId,
        @Valid @RequestBody CreateAlertRequest request) {

        log.debug("POST /prices/alerts userId={} canonicalId={} targetPrice={}",
            userId, request.getCanonicalId(), request.getTargetPrice());
        PriceAlertDTO dto = priceService.createPriceAlert(userId, request);
        return ResponseEntity.status(HttpStatus.CREATED).body(dto);
    }

    /**
     * GET /api/v1/prices/alerts
     * Returns all price alerts for the authenticated user.
     */
    @GetMapping("/alerts")
    public ResponseEntity<List<PriceAlertDTO>> getUserAlerts(
        @AuthenticationPrincipal Long userId) {

        log.debug("GET /prices/alerts userId={}", userId);
        List<PriceAlertDTO> alerts = priceService.getUserAlerts(userId);
        return ResponseEntity.ok(alerts);
    }

    /**
     * DELETE /api/v1/prices/alerts/{id}
     * Deletes a price alert. The alert must belong to the authenticated user.
     */
    @DeleteMapping("/alerts/{id}")
    public ResponseEntity<Void> deleteAlert(
        @PathVariable Long id,
        @AuthenticationPrincipal Long userId) {

        log.debug("DELETE /prices/alerts/{} userId={}", id, userId);
        priceService.deleteAlert(id, userId);
        return ResponseEntity.noContent().build();
    }
}
