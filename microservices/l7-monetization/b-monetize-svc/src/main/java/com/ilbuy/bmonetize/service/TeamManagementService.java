package com.ilbuy.bmonetize.service;

import com.ilbuy.bmonetize.domain.BSaasContract;
import com.ilbuy.bmonetize.domain.CorpMember;
import com.ilbuy.bmonetize.domain.CorpMember.MemberRole;
import com.ilbuy.bmonetize.domain.CorpMember.MemberStatus;
import com.ilbuy.bmonetize.repository.BSaasContractRepository;
import com.ilbuy.bmonetize.repository.CorpMemberRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Team / sub-account management for B端 SaaS customers.
 *
 * A corp admin can:
 *  - Add members (up to maxSeats limit from active contract)
 *  - Remove / disable members
 *  - Promote/demote roles (ADMIN ↔ MEMBER)
 *  - List all members
 *  - Check if a user belongs to the corp and has an active seat
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class TeamManagementService {

    private final CorpMemberRepository memberRepository;
    private final BSaasContractRepository contractRepository;

    @Transactional
    public CorpMember addMember(Long corpId, Long userId, String email, String name, MemberRole role, Long invitedBy) {
        if (memberRepository.existsByCorpIdAndUserId(corpId, userId)) {
            CorpMember existing = memberRepository.findByCorpIdAndUserId(corpId, userId).orElseThrow();
            if (existing.getStatus() == MemberStatus.DISABLED) {
                existing.setStatus(MemberStatus.ACTIVE);
                return memberRepository.save(existing);
            }
            throw new IllegalStateException("User " + userId + " is already a member of corp " + corpId);
        }

        enforceSeatsLimit(corpId);

        CorpMember member = CorpMember.builder()
            .corpId(corpId)
            .userId(userId)
            .userEmail(email)
            .userName(name)
            .role(role != null ? role : MemberRole.MEMBER)
            .status(MemberStatus.ACTIVE)
            .invitedBy(invitedBy)
            .build();
        memberRepository.save(member);
        log.info("[TeamMgmt] Member added: corpId={}, userId={}, role={}", corpId, userId, member.getRole());
        return member;
    }

    @Transactional
    public void removeMember(Long corpId, Long userId) {
        CorpMember member = memberRepository.findByCorpIdAndUserId(corpId, userId)
            .orElseThrow(() -> new IllegalArgumentException("Member not found: userId=" + userId + ", corpId=" + corpId));
        member.setStatus(MemberStatus.DISABLED);
        memberRepository.save(member);
        log.info("[TeamMgmt] Member disabled: corpId={}, userId={}", corpId, userId);
    }

    @Transactional
    public CorpMember updateRole(Long corpId, Long userId, MemberRole newRole) {
        CorpMember member = memberRepository.findByCorpIdAndUserId(corpId, userId)
            .orElseThrow(() -> new IllegalArgumentException("Member not found"));
        member.setRole(newRole);
        return memberRepository.save(member);
    }

    @Transactional(readOnly = true)
    public List<CorpMember> listActiveMembers(Long corpId) {
        return memberRepository.findByCorpIdAndStatus(corpId, MemberStatus.ACTIVE);
    }

    @Transactional(readOnly = true)
    public boolean isMember(Long corpId, Long userId) {
        return memberRepository.findByCorpIdAndUserId(corpId, userId)
            .map(m -> m.getStatus() == MemberStatus.ACTIVE)
            .orElse(false);
    }

    @Transactional(readOnly = true)
    public long activeSeatCount(Long corpId) {
        return memberRepository.countActiveMembers(corpId);
    }

    private void enforceSeatsLimit(Long corpId) {
        BSaasContract contract = contractRepository
            .findByCorpIdAndStatus(corpId, BSaasContract.ContractStatus.ACTIVE)
            .orElseThrow(() -> new IllegalStateException("No active SaaS contract for corp " + corpId));
        if (contract.getMaxSeats() != null) {
            long used = memberRepository.countActiveMembers(corpId);
            if (used >= contract.getMaxSeats()) {
                throw new IllegalStateException(
                    "Seat limit reached: " + used + "/" + contract.getMaxSeats() +
                    ". Upgrade your plan to add more members.");
            }
        }
    }
}
