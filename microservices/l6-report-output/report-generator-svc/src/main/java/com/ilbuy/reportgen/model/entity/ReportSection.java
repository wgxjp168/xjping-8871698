package com.ilbuy.reportgen.model.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.OffsetDateTime;

@Entity
@Table(name = "l6_report_sections")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReportSection {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "job_id", nullable = false)
    private ReportJob job;

    @Column(name = "section_key", nullable = false, length = 64)
    private String sectionKey;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(columnDefinition = "jsonb")
    private String content;

    @Column(columnDefinition = "jsonb")
    private String charts;

    @Column(name = "order_index", nullable = false)
    @Builder.Default
    private Integer orderIndex = 0;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;
}
