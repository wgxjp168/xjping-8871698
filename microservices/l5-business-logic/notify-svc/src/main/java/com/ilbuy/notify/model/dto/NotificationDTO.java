package com.ilbuy.notify.model.dto;

import com.ilbuy.notify.model.enums.NotificationChannel;
import com.ilbuy.notify.model.enums.NotificationStatus;
import com.ilbuy.notify.model.enums.NotificationType;
import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class NotificationDTO {

    private Long id;
    private Long userId;
    private NotificationChannel channel;
    private NotificationType type;
    private String title;
    private String content;
    private NotificationStatus status;
    private Integer retryCount;
    private LocalDateTime sentAt;
    private LocalDateTime createdAt;
}
