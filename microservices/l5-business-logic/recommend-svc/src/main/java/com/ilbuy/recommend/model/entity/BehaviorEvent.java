package com.ilbuy.recommend.model.entity;

import com.ilbuy.recommend.model.enums.EventType;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "behavior_events", indexes = {
    @Index(name = "idx_be_user_id", columnList = "user_id"),
    @Index(name = "idx_be_user_event_type", columnList = "user_id, event_type"),
    @Index(name = "idx_be_canonical_id", columnList = "canonical_id")
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BehaviorEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Enumerated(EnumType.STRING)
    @Column(name = "event_type", nullable = false, length = 20)
    private EventType eventType;

    @Column(name = "product_id")
    private Long productId;

    @Column(name = "canonical_id")
    private Long canonicalId;

    @Column(name = "category", length = 100)
    private String category;

    @Column(name = "platform", length = 50)
    private String platform;

    @Column(name = "keyword", length = 255)
    private String keyword;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
}
