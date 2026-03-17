package com.ilbuy.bmonetize.service;

import com.ilbuy.bmonetize.domain.BSaasContract;
import com.ilbuy.bmonetize.repository.BSaasContractRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

/**
 * API call quota enforcement for B端 SaaS API-call-package customers.
 *
 * Two-layer check:
 *  1. Persistent quota: ApiCallsUsed vs ApiCallLimit in BSaasContract (DB)
 *  2. Sliding-window rate limit via Redis (per corp, per minute)
 *
 * Call checkAndConsume() at the API gateway / filter before proxying each request.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class ApiQuotaCheckService {

    private static final String QUOTA_KEY_PREFIX    = "api:quota:corp:";
    private static final String RATE_KEY_PREFIX     = "api:rate:corp:";
    private static final int    DEFAULT_RATE_LIMIT  = 60;   // requests / minute per corp
    private static final int    RATE_WINDOW_SECONDS = 60;

    private final BSaasContractRepository contractRepository;
    private final StringRedisTemplate     redisTemplate;

    /**
     * Check and atomically consume one API call quota unit for the given corp.
     *
     * @param corpId     calling corporate ID
     * @param endpoint   endpoint being called (for logging/usage tracking)
     * @return QuotaResult indicating whether the call is allowed
     */
    public QuotaResult checkAndConsume(Long corpId, String endpoint) {
        // ---- Rate limit (Redis INCR sliding window) ----
        String rateKey = RATE_KEY_PREFIX + corpId;
        Long rateCount = redisTemplate.opsForValue().increment(rateKey);
        if (rateCount != null && rateCount == 1) {
            redisTemplate.expire(rateKey, RATE_WINDOW_SECONDS, TimeUnit.SECONDS);
        }
        if (rateCount != null && rateCount > DEFAULT_RATE_LIMIT) {
            log.warn("[ApiQuota] Rate limit exceeded: corpId={}, endpoint={}, count={}", corpId, endpoint, rateCount);
            return QuotaResult.rateLimited(DEFAULT_RATE_LIMIT);
        }

        // ---- Persistent contract quota (DB) ----
        BSaasContract contract = contractRepository
            .findByCorpIdAndStatus(corpId, BSaasContract.ContractStatus.ACTIVE)
            .orElse(null);

        if (contract == null || !contract.isValid()) {
            log.warn("[ApiQuota] No active contract: corpId={}", corpId);
            return QuotaResult.noContract();
        }

        if (!contract.hasApiQuota()) {
            log.warn("[ApiQuota] Monthly quota exhausted: corpId={}, used={}, limit={}",
                corpId, contract.getApiCallsUsed(), contract.getApiCallLimit());
            return QuotaResult.quotaExhausted(contract.getApiCallsUsed(), contract.getApiCallLimit());
        }

        // Optimistic increment in DB (updated by ApiUsageService on actual call completion)
        // Here we only gate-check; actual accounting done by ApiUsageService.recordUsage()
        return QuotaResult.allowed(contract.getApiCallLimit() - contract.getApiCallsUsed());
    }

    /**
     * Pre-check only (no consumption). Used by internal callers to surface quota info.
     */
    public QuotaResult peek(Long corpId) {
        BSaasContract c = contractRepository
            .findByCorpIdAndStatus(corpId, BSaasContract.ContractStatus.ACTIVE)
            .orElse(null);
        if (c == null || !c.isValid()) return QuotaResult.noContract();
        if (!c.hasApiQuota())          return QuotaResult.quotaExhausted(c.getApiCallsUsed(), c.getApiCallLimit());
        return QuotaResult.allowed(c.getApiCallLimit() == null ? Long.MAX_VALUE : c.getApiCallLimit() - c.getApiCallsUsed());
    }

    public record QuotaResult(
        boolean allowed,
        DenyReason denyReason,
        long remaining,
        long limit
    ) {
        static QuotaResult allowed(long remaining) {
            return new QuotaResult(true, null, remaining, -1);
        }
        static QuotaResult rateLimited(long limit) {
            return new QuotaResult(false, DenyReason.RATE_LIMITED, 0, limit);
        }
        static QuotaResult quotaExhausted(long used, Long limit) {
            return new QuotaResult(false, DenyReason.QUOTA_EXHAUSTED, 0, limit != null ? limit : -1);
        }
        static QuotaResult noContract() {
            return new QuotaResult(false, DenyReason.NO_CONTRACT, 0, 0);
        }

        public enum DenyReason { RATE_LIMITED, QUOTA_EXHAUSTED, NO_CONTRACT }
    }
}
