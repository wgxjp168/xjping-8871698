package com.ilbuy.cmonetize.controller;

import com.ilbuy.cmonetize.domain.MembershipPlan;
import com.ilbuy.cmonetize.domain.MembershipSubscription;
import com.ilbuy.cmonetize.repository.MembershipPlanRepository;
import com.ilbuy.cmonetize.service.SubscriptionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequiredArgsConstructor
public class SubscriptionController {

    private final SubscriptionService subscriptionService;
    private final MembershipPlanRepository planRepository;

    @GetMapping("/internal/v1/plans")
    public ResponseEntity<List<MembershipPlan>> getActivePlans() {
        return ResponseEntity.ok(planRepository.findByIsActiveTrue());
    }

    @GetMapping("/internal/v1/subscriptions/user/{userId}")
    public ResponseEntity<MembershipSubscription> getActiveSubscription(@PathVariable Long userId) {
        MembershipSubscription sub = subscriptionService.getActiveSubscription(userId);
        return sub != null ? ResponseEntity.ok(sub) : ResponseEntity.notFound().build();
    }

    @GetMapping("/internal/v1/subscriptions/user/{userId}/valid")
    public ResponseEntity<Boolean> hasValidSubscription(@PathVariable Long userId) {
        return ResponseEntity.ok(subscriptionService.hasValidSubscription(userId));
    }

    /** Enable or disable auto-renewal for the user's active subscription. */
    @PatchMapping("/api/v1/subscriptions/user/{userId}/auto-renew")
    public ResponseEntity<MembershipSubscription> toggleAutoRenew(
            @PathVariable Long userId,
            @RequestParam boolean enabled) {
        return ResponseEntity.ok(subscriptionService.toggleAutoRenew(userId, enabled));
    }
}
