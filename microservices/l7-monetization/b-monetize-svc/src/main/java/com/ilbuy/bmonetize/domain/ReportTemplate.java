package com.ilbuy.bmonetize.domain;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

/**
 * Customisable report template for B端 SaaS clients.
 *
 * Each corp can define its own templates that control:
 *  - Which data fields to include/exclude
 *  - Branding (logo URL, colour scheme)
 *  - Layout configuration (JSON)
 *  - Custom scoring weights
 */
@Entity
@Table(name = "report_templates", indexes = {
    @Index(name = "idx_rt_corp",   columnList = "corp_id"),
    @Index(name = "idx_rt_code",   columnList = "template_code", unique = true)
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class ReportTemplate {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "corp_id", nullable = false)
    private Long corpId;

    /** Unique code used when requesting a report from l6-report-output */
    @Column(name = "template_code", nullable = false, unique = true, length = 64)
    private String templateCode;

    @Column(name = "name", nullable = false, length = 128)
    private String name;

    @Column(name = "description", length = 512)
    private String description;

    /** JSON: logo_url, primary_colour, company_name, etc. */
    @Column(name = "branding_config", columnDefinition = "TEXT")
    private String brandingConfig;

    /**
     * JSON: array of section keys to include/exclude.
     * E.g.: {"include": ["summary","score","risk_flags"], "exclude": ["raw_data"]}
     */
    @Column(name = "section_config", columnDefinition = "TEXT")
    private String sectionConfig;

    /**
     * JSON: custom scoring weights, e.g. {"price_weight": 0.4, "quality_weight": 0.6}
     */
    @Column(name = "scoring_config", columnDefinition = "TEXT")
    private String scoringConfig;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 16)
    @Builder.Default
    private TemplateStatus status = TemplateStatus.ACTIVE;

    @Column(name = "created_by")
    private Long createdBy;

    @Column(name = "created_at", nullable = false) @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at", nullable = false) @Builder.Default
    private LocalDateTime updatedAt = LocalDateTime.now();

    @PreUpdate
    public void onUpdate() { updatedAt = LocalDateTime.now(); }

    public enum TemplateStatus { ACTIVE, ARCHIVED }
}
