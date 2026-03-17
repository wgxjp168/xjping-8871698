package com.ilbuy.bmonetize.service;

import com.ilbuy.bmonetize.domain.BSaasContract;
import com.ilbuy.bmonetize.domain.ReportTemplate;
import com.ilbuy.bmonetize.domain.ReportTemplate.TemplateStatus;
import com.ilbuy.bmonetize.repository.BSaasContractRepository;
import com.ilbuy.bmonetize.repository.ReportTemplateRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

/**
 * CRUD for corporate custom report templates.
 * Requires an active SaaS contract with plan_code that includes custom templates feature.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class ReportTemplateService {

    private final ReportTemplateRepository templateRepository;
    private final BSaasContractRepository  contractRepository;

    @Transactional
    public ReportTemplate create(Long corpId, String name, String description,
                                  String brandingConfig, String sectionConfig,
                                  String scoringConfig, Long createdBy) {
        validateActiveContract(corpId);

        String code = "TPL-" + corpId + "-" + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
        ReportTemplate template = ReportTemplate.builder()
            .corpId(corpId)
            .templateCode(code)
            .name(name)
            .description(description)
            .brandingConfig(brandingConfig)
            .sectionConfig(sectionConfig)
            .scoringConfig(scoringConfig)
            .status(TemplateStatus.ACTIVE)
            .createdBy(createdBy)
            .build();
        templateRepository.save(template);
        log.info("[ReportTemplate] Created: templateCode={}, corpId={}", code, corpId);
        return template;
    }

    @Transactional
    public ReportTemplate update(String templateCode, Long corpId,
                                  String name, String description,
                                  String brandingConfig, String sectionConfig, String scoringConfig) {
        ReportTemplate tpl = getByCode(templateCode, corpId);
        if (name        != null) tpl.setName(name);
        if (description != null) tpl.setDescription(description);
        if (brandingConfig != null) tpl.setBrandingConfig(brandingConfig);
        if (sectionConfig  != null) tpl.setSectionConfig(sectionConfig);
        if (scoringConfig  != null) tpl.setScoringConfig(scoringConfig);
        return templateRepository.save(tpl);
    }

    @Transactional
    public void archive(String templateCode, Long corpId) {
        ReportTemplate tpl = getByCode(templateCode, corpId);
        tpl.setStatus(TemplateStatus.ARCHIVED);
        templateRepository.save(tpl);
        log.info("[ReportTemplate] Archived: templateCode={}", templateCode);
    }

    @Transactional(readOnly = true)
    public List<ReportTemplate> listActive(Long corpId) {
        return templateRepository.findByCorpIdAndStatus(corpId, TemplateStatus.ACTIVE);
    }

    @Transactional(readOnly = true)
    public ReportTemplate getByCode(String templateCode) {
        return templateRepository.findByTemplateCode(templateCode)
            .orElseThrow(() -> new IllegalArgumentException("Template not found: " + templateCode));
    }

    private ReportTemplate getByCode(String templateCode, Long corpId) {
        ReportTemplate tpl = getByCode(templateCode);
        if (!tpl.getCorpId().equals(corpId)) {
            throw new IllegalArgumentException("Template " + templateCode + " does not belong to corp " + corpId);
        }
        return tpl;
    }

    private void validateActiveContract(Long corpId) {
        BSaasContract contract = contractRepository
            .findByCorpIdAndStatus(corpId, BSaasContract.ContractStatus.ACTIVE)
            .orElseThrow(() -> new IllegalStateException("No active SaaS contract for corp " + corpId));
        if (!contract.isValid()) {
            throw new IllegalStateException("SaaS contract for corp " + corpId + " has expired");
        }
    }
}
