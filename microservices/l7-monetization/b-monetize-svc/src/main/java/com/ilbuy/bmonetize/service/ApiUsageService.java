package com.ilbuy.bmonetize.service;

import com.ilbuy.bmonetize.domain.ApiUsageRecord;
import com.ilbuy.bmonetize.domain.BSaasContract;
import com.ilbuy.bmonetize.dto.RecordApiUsageRequest;
import com.ilbuy.bmonetize.repository.ApiUsageRepository;
import com.ilbuy.bmonetize.repository.BSaasContractRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class ApiUsageService {

    private static final BigDecimal API_UNIT_PRICE = new BigDecimal("0.0100");  // ¥0.01/call
    private final ApiUsageRepository apiUsageRepository;
    private final BSaasContractRepository contractRepository;

    @Transactional
    public void recordUsage(RecordApiUsageRequest req) {
        String period = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM"));
        BSaasContract contract = req.getContractNo() != null
            ? contractRepository.findByContractNo(req.getContractNo()).orElse(null)
            : contractRepository.findByCorpIdAndStatus(req.getCorpId(), BSaasContract.ContractStatus.ACTIVE).orElse(null);

        if (contract != null && contract.hasApiQuota()) {
            contract.setApiCallsUsed(contract.getApiCallsUsed() + req.getCallCount());
            contractRepository.save(contract);
        }

        ApiUsageRecord record = ApiUsageRecord.builder()
            .corpId(req.getCorpId())
            .contractNo(contract != null ? contract.getContractNo() : null)
            .endpoint(req.getEndpoint())
            .callCount(req.getCallCount())
            .billingPeriod(period)
            .unitPrice(API_UNIT_PRICE)
            .amount(API_UNIT_PRICE.multiply(BigDecimal.valueOf(req.getCallCount())))
            .build();
        apiUsageRepository.save(record);
        log.debug("[ApiUsage] Recorded: corpId={}, endpoint={}, calls={}", req.getCorpId(), req.getEndpoint(), req.getCallCount());
    }

    @Transactional(readOnly = true)
    public Map<String, Object> getMonthlyUsage(Long corpId, String period) {
        Long total = apiUsageRepository.sumCallsByCorpAndPeriod(corpId, period);
        List<ApiUsageRecord> records = apiUsageRepository.findByCorpIdAndBillingPeriod(corpId, period);
        BigDecimal totalAmount = records.stream()
            .map(r -> r.getAmount() != null ? r.getAmount() : BigDecimal.ZERO)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
        return Map.of(
            "corpId", corpId,
            "period", period,
            "totalCalls", total != null ? total : 0L,
            "totalAmount", totalAmount,
            "records", records
        );
    }
}
