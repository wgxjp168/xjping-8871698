package com.ilbuy.product.model.entity;

import jakarta.persistence.*;
import lombok.*;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.Instant;

@Entity
@Table(
    name = "category",
    indexes = {
        @Index(name = "idx_category_parent_id", columnList = "parent_id"),
        @Index(name = "idx_category_name",      columnList = "name")
    }
)
@EntityListeners(AuditingEntityListener.class)
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Category {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 128)
    private String name;

    /** null means root category */
    @Column(name = "parent_id")
    private Long parentId;

    @Column(length = 512)
    private String description;

    @Column(name = "sort_order")
    @Builder.Default
    private Integer sortOrder = 0;

    @Column(name = "icon_url", length = 512)
    private String iconUrl;

    @Column(nullable = false)
    @Builder.Default
    private Boolean enabled = true;

    @CreatedDate
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @LastModifiedDate
    @Column(name = "updated_at")
    private Instant updatedAt;
}
