package com.ilbuy.format.model.entity;

import com.ilbuy.format.model.enums.FormatJobStatus;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.OffsetDateTime;

@Entity
@Table(name = "l6_format_jobs")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FormatJob {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "format_job_no", nullable = false, unique = true, length = 64)
    private String formatJobNo;

    @Column(name = "generator_job_no", nullable = false, length = 64)
    private String generatorJobNo;

    @Column(name = "l5_report_no", nullable = false, length = 64)
    private String l5ReportNo;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(name = "client_type", nullable = false, length = 32)
    private String clientType;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    @Builder.Default
    private FormatJobStatus status = FormatJobStatus.PENDING;

    @Column(name = "error_message")
    private String errorMessage;

    @Column(name = "html_url", length = 512)
    private String htmlUrl;

    @Column(name = "html_size")
    private Long htmlSize;

    @Column(name = "pdf_url", length = 512)
    private String pdfUrl;

    @Column(name = "pdf_size")
    private Long pdfSize;

    @Column(name = "excel_url", length = 512)
    private String excelUrl;

    @Column(name = "excel_size")
    private Long excelSize;

    @Column(name = "expires_at")
    private OffsetDateTime expiresAt;

    @Column(name = "started_at")
    private OffsetDateTime startedAt;

    @Column(name = "completed_at")
    private OffsetDateTime completedAt;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private OffsetDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;
}
