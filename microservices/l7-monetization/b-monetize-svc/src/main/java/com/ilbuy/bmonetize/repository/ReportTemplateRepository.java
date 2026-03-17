package com.ilbuy.bmonetize.repository;

import com.ilbuy.bmonetize.domain.ReportTemplate;
import com.ilbuy.bmonetize.domain.ReportTemplate.TemplateStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface ReportTemplateRepository extends JpaRepository<ReportTemplate, Long> {
    List<ReportTemplate> findByCorpIdAndStatus(Long corpId, TemplateStatus status);
    Optional<ReportTemplate> findByTemplateCode(String templateCode);
    boolean existsByCorpIdAndTemplateCode(Long corpId, String templateCode);
}
