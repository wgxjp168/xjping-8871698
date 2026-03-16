package com.ilbuy.contract.model.entity;

import com.ilbuy.contract.model.enums.InvoiceStatus;
import com.ilbuy.contract.model.enums.InvoiceType;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Entity
@Table(name = "invoice")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Invoice {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "invoice_no", unique = true, length = 30)
    private String invoiceNo;

    @Column(name = "contract_id", nullable = false)
    private Long contractId;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private InvoiceType type;

    @Column(nullable = false, precision = 18, scale = 2)
    private BigDecimal amount;

    @Column(name = "tax_rate", nullable = false, precision = 5, scale = 4)
    private BigDecimal taxRate;

    @Column(name = "tax_amount", precision = 18, scale = 2)
    private BigDecimal taxAmount;

    @Column(name = "invoice_title", nullable = false, length = 300)
    private String invoiceTitle;

    @Column(name = "taxpayer_id", length = 50)
    private String taxpayerId;

    @Column(name = "bank_account", length = 100)
    private String bankAccount;

    @Column(name = "bank_name", length = 200)
    private String bankName;

    @Column(name = "company_address", length = 300)
    private String companyAddress;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private InvoiceStatus status;

    @Column(name = "issue_date")
    private LocalDate issueDate;

    @Column(name = "mailing_address", length = 500)
    private String mailingAddress;

    @Column(name = "tracking_no", length = 100)
    private String trackingNo;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;
}
