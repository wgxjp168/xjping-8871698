package com.ilbuy.notify.service;

import com.ilbuy.notify.channel.EmailChannelAdapter;
import com.ilbuy.notify.channel.SmsChannelAdapter;
import com.ilbuy.notify.channel.WechatChannelAdapter;
import com.ilbuy.notify.model.dto.NotificationDTO;
import com.ilbuy.notify.model.dto.PageResult;
import com.ilbuy.notify.model.dto.SendNotificationRequest;
import com.ilbuy.notify.model.entity.Notification;
import com.ilbuy.notify.model.enums.NotificationChannel;
import com.ilbuy.notify.model.enums.NotificationStatus;
import com.ilbuy.notify.model.enums.NotificationType;
import com.ilbuy.notify.repository.NotificationRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class NotificationService {

    private final NotificationRepository notificationRepository;
    private final SmsChannelAdapter smsChannelAdapter;
    private final EmailChannelAdapter emailChannelAdapter;
    private final WechatChannelAdapter wechatChannelAdapter;

    /**
     * Send a notification via the specified channel and persist the record.
     */
    @Transactional
    public NotificationDTO send(SendNotificationRequest request) {
        Map<String, String> variables = request.getVariables() != null ? request.getVariables() : Map.of();

        String title   = buildTitle(request.getType(), variables);
        String content = buildContent(request.getType(), variables);

        Notification notification = Notification.builder()
            .userId(request.getUserId())
            .channel(request.getChannel())
            .type(request.getType())
            .title(title)
            .content(content)
            .status(NotificationStatus.PENDING)
            .retryCount(0)
            .build();

        notification = notificationRepository.save(notification);

        // Dispatch via channel adapter
        try {
            dispatch(notification, variables);
            notification.setStatus(NotificationStatus.SENT);
            notification.setSentAt(LocalDateTime.now());
        } catch (Exception e) {
            log.error("Failed to dispatch notification id={}: {}", notification.getId(), e.getMessage());
            notification.setStatus(NotificationStatus.FAILED);
            notification.setRetryCount(notification.getRetryCount() + 1);
        }

        notification = notificationRepository.save(notification);
        log.info("Notification {} dispatched via {} for userId={}", notification.getId(), request.getChannel(), request.getUserId());
        return toDTO(notification);
    }

    /**
     * Convenience method called internally by MQ consumers.
     */
    @Transactional
    public void sendInternal(Long userId, NotificationChannel channel, NotificationType type,
                             Map<String, String> variables) {
        SendNotificationRequest req = new SendNotificationRequest();
        req.setUserId(userId);
        req.setChannel(channel);
        req.setType(type);
        req.setVariables(variables);
        send(req);
    }

    /**
     * List current user's notifications (paginated).
     */
    @Transactional(readOnly = true)
    public PageResult<NotificationDTO> listNotifications(Long userId, int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        Page<Notification> notifPage = notificationRepository.findByUserIdOrderByCreatedAtDesc(userId, pageable);
        return PageResult.<NotificationDTO>builder()
            .content(notifPage.getContent().stream().map(this::toDTO).toList())
            .page(notifPage.getNumber())
            .size(notifPage.getSize())
            .totalElements(notifPage.getTotalElements())
            .totalPages(notifPage.getTotalPages())
            .first(notifPage.isFirst())
            .last(notifPage.isLast())
            .build();
    }

    /**
     * Mark a single notification as READ. Must belong to the current user.
     */
    @Transactional
    public NotificationDTO markRead(Long userId, Long notificationId) {
        Notification notification = notificationRepository.findById(notificationId)
            .orElseThrow(() -> new IllegalArgumentException("通知不存在: " + notificationId));

        if (!notification.getUserId().equals(userId)) {
            throw new IllegalArgumentException("无权操作该通知");
        }

        notification.setStatus(NotificationStatus.READ);
        notification = notificationRepository.save(notification);
        return toDTO(notification);
    }

    /**
     * Mark all notifications as READ for the current user.
     */
    @Transactional
    public int markAllRead(Long userId) {
        return notificationRepository.markAllReadByUserId(userId);
    }

    /**
     * Get unread count for the current user. "Unread" means status != READ.
     */
    @Transactional(readOnly = true)
    public long getUnreadCount(Long userId) {
        return notificationRepository.countByUserIdAndStatusNot(userId, NotificationStatus.READ);
    }

    // ---- private helpers ----

    private void dispatch(Notification notification, Map<String, String> variables) {
        switch (notification.getChannel()) {
            case SMS -> {
                String phone = variables.getOrDefault("phone", "unknown");
                smsChannelAdapter.send(phone, notification.getContent());
            }
            case EMAIL -> {
                String email = variables.getOrDefault("email", "unknown");
                emailChannelAdapter.send(email, notification.getTitle(), notification.getContent());
            }
            case WECHAT -> {
                String openId     = variables.getOrDefault("openId", "unknown");
                String templateId = variables.getOrDefault("templateId", "default");
                wechatChannelAdapter.send(openId, templateId, notification.getContent());
            }
        }
    }

    private String buildTitle(NotificationType type, Map<String, String> variables) {
        return switch (type) {
            case ORDER_STATUS  -> "订单状态变更通知";
            case REPORT_READY  -> "报告已生成，可以下载";
            case SYSTEM        -> variables.getOrDefault("title", "系统通知");
        };
    }

    private String buildContent(NotificationType type, Map<String, String> variables) {
        return switch (type) {
            case ORDER_STATUS -> {
                String orderId = variables.getOrDefault("orderId", "");
                String status  = variables.getOrDefault("status", "");
                yield String.format("您的订单 %s 状态已更新为：%s", orderId, status);
            }
            case REPORT_READY -> {
                String reportNo = variables.getOrDefault("reportNo", "");
                String title    = variables.getOrDefault("title", "");
                yield String.format("您申请的报告《%s》（编号：%s）已生成完毕，请登录平台下载。", title, reportNo);
            }
            case SYSTEM -> variables.getOrDefault("content", "系统消息");
        };
    }

    private NotificationDTO toDTO(Notification notification) {
        return NotificationDTO.builder()
            .id(notification.getId())
            .userId(notification.getUserId())
            .channel(notification.getChannel())
            .type(notification.getType())
            .title(notification.getTitle())
            .content(notification.getContent())
            .status(notification.getStatus())
            .retryCount(notification.getRetryCount())
            .sentAt(notification.getSentAt())
            .createdAt(notification.getCreatedAt())
            .build();
    }
}
