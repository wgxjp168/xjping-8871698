package com.ilbuy.report.model.entity;

import com.ilbuy.report.model.enums.ReportStatus;
import com.ilbuy.report.model.enums.ReportType;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "reports")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Report {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "report_no", nullable = false, unique = true, length = 64)
    private String reportNo;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false, length = 255)
    private String title;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private ReportType type;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private ReportStatus status;

    @Column(name = "file_url", length = 512)
    private String fileUrl;

    @Column(name = "file_size")
    private Long fileSize;

    @Column(name = "expires_at")
    private LocalDateTime expiresAt;

    @Column(name = "deleted", nullable = false)
    @Builder.Default
    private Boolean deleted = false;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
