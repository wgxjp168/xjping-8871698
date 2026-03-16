package com.ilbuy.notify.model.dto;

import com.ilbuy.notify.model.enums.NotificationChannel;
import com.ilbuy.notify.model.enums.NotificationType;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.Map;

@Data
public class SendNotificationRequest {

    @NotNull(message = "userId不能为空")
    private Long userId;

    @NotNull(message = "渠道不能为空")
    private NotificationChannel channel;

    @NotNull(message = "通知类型不能为空")
    private NotificationType type;

    private Map<String, String> variables;
}
