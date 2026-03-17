package com.ilbuy.cmonetize.service;

import com.ilbuy.cmonetize.domain.MembershipPlan;
import com.ilbuy.cmonetize.domain.MembershipSubscription;
import com.ilbuy.cmonetize.domain.MembershipSubscription.SubscriptionStatus;
import com.ilbuy.cmonetize.dto.SubscribeRequest;
import com.ilbuy.cmonetize.repository.MembershipPlanRepository;
import com.ilbuy.cmonetize.repository.MembershipSubscriptionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class SubscriptionService {

    private final MembershipSubscriptionRepository subscriptionRepository;
    private final MembershipPlanRepository planRepository;
    private final CMonetizeService cMonetizeService;

    @Transactional
    public MembershipSubscription activateSubscription(Long userId, String planCode, String orderNo) {
        MembershipPlan plan = planRepository.findByPlanCode(planCode)
            .orElseThrow(() -> new IllegalArgumentException("Plan not found: " + planCode));

        // Cancel existing active subscription if any
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
        log.info("[Subscription] Activated: subscriptionNo={}, userId={}, plan={}, endDate={}", subscriptionNo, userId, planCode, sub.getEndDate());
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

    /** Daily job to expire ended subscriptions */
    @Scheduled(cron = "0 0 1 * * *")
    @Transactional
    public void expireSubscriptions() {
        List<MembershipSubscription> actives = subscriptionRepository.findAll().stream()
            .filter(s -> s.getStatus() == SubscriptionStatus.ACTIVE && LocalDate.now().isAfter(s.getEndDate()))
            .toList();
        actives.forEach(s -> {
            s.setStatus(SubscriptionStatus.EXPIRED);
            subscriptionRepository.save(s);
            log.info("[Subscription] Expired: subscriptionNo={}", s.getSubscriptionNo());
        });
    }
}
