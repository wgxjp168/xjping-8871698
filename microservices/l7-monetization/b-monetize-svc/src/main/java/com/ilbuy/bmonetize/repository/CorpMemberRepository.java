package com.ilbuy.bmonetize.repository;

import com.ilbuy.bmonetize.domain.CorpMember;
import com.ilbuy.bmonetize.domain.CorpMember.MemberStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;
import java.util.Optional;

public interface CorpMemberRepository extends JpaRepository<CorpMember, Long> {
    List<CorpMember> findByCorpId(Long corpId);
    List<CorpMember> findByCorpIdAndStatus(Long corpId, MemberStatus status);
    Optional<CorpMember> findByCorpIdAndUserId(Long corpId, Long userId);
    boolean existsByCorpIdAndUserId(Long corpId, Long userId);

    @Query("SELECT COUNT(m) FROM CorpMember m WHERE m.corpId = :corpId AND m.status = 'ACTIVE'")
    long countActiveMembers(Long corpId);
}
