package com.ilbuy.bmonetize.controller;

import com.ilbuy.bmonetize.domain.ReportTemplate;
import com.ilbuy.bmonetize.service.ReportTemplateService;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Custom report template management API (B端 SaaS).
 */
@RestController
@RequestMapping("/api/v1/corps/{corpId}/report-templates")
@RequiredArgsConstructor
@Slf4j
public class ReportTemplateController {

    private final ReportTemplateService templateService;

    @GetMapping
    public ResponseEntity<List<ReportTemplate>> list(@PathVariable Long corpId) {
        return ResponseEntity.ok(templateService.listActive(corpId));
    }

    @PostMapping
    public ResponseEntity<ReportTemplate> create(@PathVariable Long corpId,
                                                  @Valid @RequestBody CreateTemplateRequest req) {
        log.info("[TemplateAPI] Create: corpId={}, name={}", corpId, req.getName());
        return ResponseEntity.ok(templateService.create(
            corpId, req.getName(), req.getDescription(),
            req.getBrandingConfig(), req.getSectionConfig(), req.getScoringConfig(),
            req.getCreatedBy()));
    }

    @PutMapping("/{templateCode}")
    public ResponseEntity<ReportTemplate> update(@PathVariable Long corpId,
                                                  @PathVariable String templateCode,
                                                  @RequestBody CreateTemplateRequest req) {
        return ResponseEntity.ok(templateService.update(
            templateCode, corpId, req.getName(), req.getDescription(),
            req.getBrandingConfig(), req.getSectionConfig(), req.getScoringConfig()));
    }

    @DeleteMapping("/{templateCode}")
    public ResponseEntity<Void> archive(@PathVariable Long corpId,
                                         @PathVariable String templateCode) {
        templateService.archive(templateCode, corpId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/{templateCode}")
    public ResponseEntity<ReportTemplate> get(@PathVariable Long corpId,
                                               @PathVariable String templateCode) {
        ReportTemplate tpl = templateService.getByCode(templateCode);
        return ResponseEntity.ok(tpl);
    }

    @Data
    public static class CreateTemplateRequest {
        @NotBlank private String name;
        private String description;
        /** JSON string: {"logo_url":"...","primary_colour":"#FF6B35","company_name":"..."} */
        private String brandingConfig;
        /** JSON string: {"include":["summary","score"],"exclude":["raw_data"]} */
        private String sectionConfig;
        /** JSON string: {"price_weight":0.4,"quality_weight":0.6} */
        private String scoringConfig;
        private Long   createdBy;
    }
}
