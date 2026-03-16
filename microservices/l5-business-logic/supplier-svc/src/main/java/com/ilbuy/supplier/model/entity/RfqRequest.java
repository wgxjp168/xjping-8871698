package com.ilbuy.supplier.model.entity;

import com.ilbuy.supplier.model.enums.RfqStatus;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "rfq_request")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class RfqRequest {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "rfq_no", nullable = false, unique = true, length = 30)
    private String rfqNo;

    @Column(name = "buyer_user_id", nullable = false)
    private Long buyerUserId;

    @Column(name = "supplier_no", nullable = false, length = 30)
    private String supplierNo;

    @Column(name = "product_description", nullable = false, columnDefinition = "TEXT")
    private String productDescription;

    @Column(name = "canonical_id", length = 100)
    private String canonicalId;

    @Column(name = "quantity", nullable = false)
    private Integer quantity;

    @Column(name = "unit", nullable = false, length = 20)
    private String unit;

    @Column(name = "required_delivery_date", nullable = false)
    private LocalDate requiredDeliveryDate;

    @Column(name = "delivery_address", nullable = false)
    private String deliveryAddress;

    @Column(name = "budget_amount", precision = 19, scale = 2)
    private BigDecimal budgetAmount;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private RfqStatus status;

    @Column(name = "buyer_remark")
    private String buyerRemark;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
