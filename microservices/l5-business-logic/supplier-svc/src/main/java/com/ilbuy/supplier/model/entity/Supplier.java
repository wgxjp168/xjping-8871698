package com.ilbuy.supplier.model.entity;

import com.ilbuy.supplier.model.enums.SupplierStatus;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "supplier")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Supplier {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "supplier_no", nullable = false, unique = true, length = 30)
    private String supplierNo;

    @Column(name = "company_name", nullable = false, length = 200)
    private String companyName;

    @Column(name = "contact_name", nullable = false, length = 100)
    private String contactName;

    @Column(name = "contact_email", nullable = false, length = 200)
    private String contactEmail;

    @Column(name = "contact_phone", length = 30)
    private String contactPhone;

    @Column(name = "business_license", nullable = false, unique = true, length = 100)
    private String businessLicense;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private SupplierStatus status;

    @Column(name = "average_score", precision = 5, scale = 2)
    private BigDecimal averageScore;

    @Column(name = "total_coop_count")
    private Integer totalCoopCount;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
