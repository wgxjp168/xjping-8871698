package com.ilbuy.notify.model.entity;

import com.ilbuy.notify.model.enums.NotificationChannel;
import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "notification_templates")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NotificationTemplate {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "template_code", nullable = false, unique = true, length = 64)
    private String templateCode;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 16)
    private NotificationChannel channel;

    @Column(name = "title_template", nullable = false, length = 255)
    private String titleTemplate;

    @Column(name = "content_template", nullable = false, columnDefinition = "TEXT")
    private String contentTemplate;

    /**
     * Comma-separated list of variable names used in the templates, e.g. "orderId,status".
     */
    @Column(name = "variables", length = 512)
    private String variables;
}
