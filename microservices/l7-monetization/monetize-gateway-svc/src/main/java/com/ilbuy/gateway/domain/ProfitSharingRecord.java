package com.ilbuy.gateway.domain;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * Tracks a profit-sharing (分账) request and its result.
 * Supports WeChat Pay V3 and Alipay settlement.
 */
@Entity
@Table(name = "profit_sharing_records", indexes = {
    @Index(name = "idx_ps_payment_no", columnList = "payment_no"),
    @Index(name = "idx_ps_order_no",   columnList = "order_no", unique = true)
})
@Getter @Setter @Builder @NoArgsConstructor @AllArgsConstructor
public class ProfitSharingRecord {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** Internal sharing order number */
    @Column(name = "order_no", nullable = false, unique = true, length = 64)
    private String orderNo;

    /** Original payment number */
    @Column(name = "payment_no", nullable = false, length = 64)
    private String paymentNo;

    /** Payment channel transaction ID (e.g. WeChat transaction_id) */
    @Column(name = "channel_order_no", length = 128)
    private String channelOrderNo;

    /** Payment channel: WECHAT / ALIPAY */
    @Enumerated(EnumType.STRING)
    @Column(name = "channel", nullable = false, length = 16)
    private PaymentOrder.PaymentChannel channel;

    /** Total amount being shared (CNY) */
    @Column(name = "total_amount", nullable = false, precision = 12, scale = 2)
    private BigDecimal totalAmount;

    /**
     * Receivers JSON array, e.g.:
     * [{"account":"merchant_openid","amount":1000,"description":"平台服务费"}]
     */
    @Column(name = "receivers_json", columnDefinition = "TEXT")
    private String receiversJson;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 32)
    private SharingStatus status;

    /** Channel-returned sharing ID for query/return operations */
    @Column(name = "channel_sharing_id", length = 128)
    private String channelSharingId;

    /** Raw response from the channel */
    @Column(name = "channel_resp", columnDefinition = "TEXT")
    private String channelResp;

    @Column(name = "created_at", nullable = false)
    @Builder.Default
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "finished_at")
    private LocalDateTime finishedAt;

    public enum SharingStatus {
        PENDING,       // awaiting initiation
        PROCESSING,    // sent to channel, awaiting result
        SUCCESS,       // sharing complete
        FAILED,        // channel rejected
        RETURNED       // funds returned from sharing
    }
}
