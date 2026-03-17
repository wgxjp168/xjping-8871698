package com.ilbuy.bmonetize.controller;

import com.ilbuy.bmonetize.domain.CorpMember;
import com.ilbuy.bmonetize.domain.CorpMember.MemberRole;
import com.ilbuy.bmonetize.service.TeamManagementService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * B端 Team management API.
 * Corp admin manages sub-accounts (seats) under the SaaS contract.
 */
@RestController
@RequestMapping("/api/v1/corps/{corpId}/members")
@RequiredArgsConstructor
@Slf4j
public class TeamController {

    private final TeamManagementService teamManagementService;

    /** List all active team members. */
    @GetMapping
    public ResponseEntity<List<CorpMember>> listMembers(@PathVariable Long corpId) {
        return ResponseEntity.ok(teamManagementService.listActiveMembers(corpId));
    }

    /** Add a new team member (seat). */
    @PostMapping
    public ResponseEntity<CorpMember> addMember(@PathVariable Long corpId,
                                                 @Valid @RequestBody AddMemberRequest req) {
        log.info("[TeamAPI] Add member: corpId={}, userId={}", corpId, req.getUserId());
        CorpMember member = teamManagementService.addMember(
            corpId, req.getUserId(), req.getUserEmail(), req.getUserName(),
            req.getRole(), req.getInvitedBy());
        return ResponseEntity.ok(member);
    }

    /** Remove (disable) a member. */
    @DeleteMapping("/{userId}")
    public ResponseEntity<Void> removeMember(@PathVariable Long corpId,
                                              @PathVariable Long userId) {
        log.info("[TeamAPI] Remove member: corpId={}, userId={}", corpId, userId);
        teamManagementService.removeMember(corpId, userId);
        return ResponseEntity.noContent().build();
    }

    /** Update member role (ADMIN / MEMBER). */
    @PatchMapping("/{userId}/role")
    public ResponseEntity<CorpMember> updateRole(@PathVariable Long corpId,
                                                  @PathVariable Long userId,
                                                  @RequestBody Map<String, String> body) {
        MemberRole role = MemberRole.valueOf(body.get("role").toUpperCase());
        return ResponseEntity.ok(teamManagementService.updateRole(corpId, userId, role));
    }

    /** Get current seat usage. */
    @GetMapping("/stats")
    public ResponseEntity<Map<String, Object>> stats(@PathVariable Long corpId) {
        return ResponseEntity.ok(Map.of(
            "corpId", corpId,
            "activeSeatCount", teamManagementService.activeSeatCount(corpId)
        ));
    }

    @Data
    public static class AddMemberRequest {
        @NotNull private Long    userId;
        private String  userEmail;
        private String  userName;
        private MemberRole role;
        private Long    invitedBy;
    }
}
