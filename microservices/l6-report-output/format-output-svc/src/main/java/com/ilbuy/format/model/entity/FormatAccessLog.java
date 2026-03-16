package com.ilbuy.format.model.entity;

import com.ilbuy.format.model.enums.FormatType;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.OffsetDateTime;

/**
 * Records every access to a formatted report file (HTML view, PDF download, Excel download).
 * Supports audit, analytics, and billing by access count.
 */
@Entity
@Table(name = "l6_format_access_log")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FormatAccessLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "format_job_id", nullable = false)
    private FormatJob formatJob;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private FormatType format;

    @Column(name = "ip_address", length = 64)
    private String ipAddress;

    @Column(name = "user_agent", length = 512)
    private String userAgent;

    @CreationTimestamp
    @Column(name = "accessed_at", nullable = false, updatable = false)
    private OffsetDateTime accessedAt;
}
