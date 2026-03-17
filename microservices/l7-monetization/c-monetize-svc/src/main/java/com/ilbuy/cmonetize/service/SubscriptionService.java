package com.ilbuy.cmonetize.service;

import com.ilbuy.cmonetize.domain.CMonetizeOrder;
import com.ilbuy.cmonetize.domain.MembershipPlan;
import com.ilbuy.cmonetize.domain.MembershipSubscription;
import com.ilbuy.cmonetize.domain.MembershipSubscription.SubscriptionStatus;
import com.ilbuy.cmonetize.dto.CreateOrderRequest;
import com.ilbuy.cmonetize.repository.MembershipPlanRepository;
import com.ilbuy.cmonetize.repository.MembershipSubscriptionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class SubscriptionService {

    private final MembershipSubscriptionRepository subscriptionRepository;
    private final MembershipPlanRepository         planRepository;
    private final CMonetizeService                 cMonetizeService;

    @Transactional
    public MembershipSubscription activateSubscription(Long userId, String planCode, String orderNo) {
        MembershipPlan plan = planRepository.findByPlanCode(planCode)
            .orElseThrow(() -> new IllegalArgumentException("Plan not found: " + planCode));

        // Cancel existing active subscription
        subscriptionRepository.findByUserIdAndStatus(userId, SubscriptionStatus.ACTIVE)
            .ifPresent(existing -> {
                existing.setStatus(SubscriptionStatus.CANCELLED);
                subscriptionRepository.save(existing);
            });

        LocalDate start = LocalDate.now();
        String subscriptionNo = "SUB-" + UUID.randomUUID().toString().replace("-", "").toUpperCase().substring(0, 16);

        MembershipSubscription sub = MembershipSubscription.builder()
            .subscriptionNo(subscriptionNo)
            .userId(userId)
            .planCode(planCode)
            .startDate(start)
            .endDate(start.plusMonths(plan.getDurationMonths()))
            .status(SubscriptionStatus.ACTIVE)
            .autoRenew(false)
            .orderNo(orderNo)
            .build();
        subscriptionRepository.save(sub);
        log.info("[Subscription] Activated: subscriptionNo={}, userId={}, plan={}, endDate={}",
            subscriptionNo, userId, planCode, sub.getEndDate());
        return sub;
    }

    @Transactional
    public MembershipSubscription toggleAutoRenew(Long userId, boolean autoRenew) {
        MembershipSubscription sub = subscriptionRepository
            .findByUserIdAndStatus(userId, SubscriptionStatus.ACTIVE)
            .orElseThrow(() -> new IllegalArgumentException("No active subscription for user " + userId));
        sub.setAutoRenew(autoRenew);
        subscriptionRepository.save(sub);
        log.info("[Subscription] AutoRenew set to {} for subscriptionNo={}", autoRenew, sub.getSubscriptionNo());
        return sub;
    }

    @Transactional(readOnly = true)
    public MembershipSubscription getActiveSubscription(Long userId) {
        return subscriptionRepository.findByUserIdAndStatus(userId, SubscriptionStatus.ACTIVE).orElse(null);
    }

    @Transactional(readOnly = true)
    public boolean hasValidSubscription(Long userId) {
        MembershipSubscription sub = getActiveSubscription(userId);
        return sub != null && sub.isValid();
    }

    /**
     * Daily scheduler — runs at 02:00 each day.
     *
     * Pass 1: auto-renew subscriptions expiring today or tomorrow.
     *   Attempts payment via CMonetizeService. On success the new order's payment
     *   event listener calls activateSubscription() which extends endDate.
     *   On failure the subscription is left active until actual expiry;
     *   a warning log is emitted so ops can monitor.
     *
     * Pass 2: expire subscriptions whose endDate has already passed.
     */
    @Scheduled(cron = "0 0 2 * * *")
    @Transactional
    public void dailyRenewalAndExpiry() {
        LocalDate today    = LocalDate.now();
        LocalDate tomorrow = today.plusDays(1);

        // ----- Auto-renewal pass -----
        List<MembershipSubscription> renewCandidates =
            subscriptionRepository.findByStatusAndAutoRenewTrue(SubscriptionStatus.ACTIVE);

        for (MembershipSubscription sub : renewCandidates) {
            if (!sub.getEndDate().isBefore(tomorrow)) continue; // not due yet

            MembershipPlan plan = planRepository.findByPlanCode(sub.getPlanCode()).orElse(null);
            if (plan == null) {
                log.warn("[Subscription] Plan not found for renewal: {}", sub.getPlanCode());
                continue;
            }

            try {
                // Create a new auto-renewal order (no payment channel — deducted from saved card/wallet)
                CreateOrderRequest req = new CreateOrderRequest();
                req.setUserId(sub.getUserId());
                req.setProductType(CMonetizeOrder.ProductType.MEMBERSHIP);
                req.setProductId(sub.getPlanCode());
                req.setPaymentChannel("AUTO_RENEWAL");

                cMonetizeService.createOrder(req);
                log.info("[Subscription] Auto-renewal order created: userId={}, plan={}", sub.getUserId(), sub.getPlanCode());
            } catch (Exception e) {
                // Non-fatal: subscription continues until end, ops alerted
                log.error("[Subscription] Auto-renewal failed for userId={}, plan={}: {}",
                    sub.getUserId(), sub.getPlanCode(), e.getMessage());
            }
        }

        // ----- Expiry pass -----
        List<MembershipSubscription> actives = subscriptionRepository
            .findAll().stream()
            .filter(s -> s.getStatus() == SubscriptionStatus.ACTIVE && today.isAfter(s.getEndDate()))
            .toList();

        actives.forEach(s -> {
            s.setStatus(SubscriptionStatus.EXPIRED);
            subscriptionRepository.save(s);
            log.info("[Subscription] Expired: subscriptionNo={}, userId={}", s.getSubscriptionNo(), s.getUserId());
        });

        log.info("[Subscription] Daily job done: renewAttempts={}, expired={}", renewCandidates.size(), actives.size());
    }
}
