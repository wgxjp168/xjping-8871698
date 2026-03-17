package com.ilbuy.cmonetize.repository;

import com.ilbuy.cmonetize.domain.MembershipPlan;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface MembershipPlanRepository extends JpaRepository<MembershipPlan, Long> {
    Optional<MembershipPlan> findByPlanCode(String planCode);
    List<MembershipPlan> findByIsActiveTrue();
}
