package com.ilbuy.order.model.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;

@Entity
@Table(
    name = "order_items",
    indexes = {
        @Index(name = "idx_order_id",     columnList = "order_id"),
        @Index(name = "idx_canonical_id", columnList = "canonical_id")
    }
)
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class OrderItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id", nullable = false)
    @ToString.Exclude
    @EqualsAndHashCode.Exclude
    private Order order;

    /** 来自 L4 data-svc 的跨平台唯一商品 ID */
    @Column(name = "canonical_id", nullable = false, length = 64)
    private String canonicalId;

    @Column(name = "platform", nullable = false, length = 32)
    private String platform;

    @Column(name = "product_title", nullable = false, columnDefinition = "TEXT")
    private String productTitle;

    /** 购买时的单价快照 */
    @Column(name = "unit_price", nullable = false, precision = 12, scale = 2)
    private BigDecimal unitPrice;

    @Column(nullable = false)
    private Integer quantity;

    @Column(name = "subtotal", nullable = false, precision = 14, scale = 2)
    private BigDecimal subtotal;

    /** 规格快照 JSON, e.g. {"颜色":"黑色","存储":"256GB"} */
    @Column(columnDefinition = "JSON")
    private String specs;

    /** 商品主图快照 URL */
    @Column(name = "image_url", length = 512)
    private String imageUrl;
}
