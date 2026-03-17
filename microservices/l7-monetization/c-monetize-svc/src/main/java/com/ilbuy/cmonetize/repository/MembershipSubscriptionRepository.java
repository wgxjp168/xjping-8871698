package com.ilbuy.cmonetize.repository;

import com.ilbuy.cmonetize.domain.MembershipSubscription;
import com.ilbuy.cmonetize.domain.MembershipSubscription.SubscriptionStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface MembershipSubscriptionRepository extends JpaRepository<MembershipSubscription, Long> {
    Optional<MembershipSubscription> findBySubscriptionNo(String subscriptionNo);
    Optional<MembershipSubscription> findByUserIdAndStatus(Long userId, SubscriptionStatus status);
    List<MembershipSubscription> findByUserIdOrderByCreatedAtDesc(Long userId);
}
