package com.ilbuy.notify.api;

import com.ilbuy.notify.model.dto.NotificationDTO;
import com.ilbuy.notify.model.dto.PageResult;
import com.ilbuy.notify.model.dto.SendNotificationRequest;
import com.ilbuy.notify.service.NotificationService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/notifications")
@RequiredArgsConstructor
@Slf4j
public class NotificationController {

    private final NotificationService notificationService;

    /**
     * POST /api/v1/notifications/send – send notification (ADMIN or service-to-service only)
     */
    @PostMapping("/send")
    public ResponseEntity<NotificationDTO> send(@Valid @RequestBody SendNotificationRequest request) {
        NotificationDTO dto = notificationService.send(request);
        return ResponseEntity.ok(dto);
    }

    /**
     * GET /api/v1/notifications – list current user's notifications (paginated)
     */
    @GetMapping
    public ResponseEntity<PageResult<NotificationDTO>> listNotifications(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        PageResult<NotificationDTO> result = notificationService.listNotifications(userId, page, size);
        return ResponseEntity.ok(result);
    }

    /**
     * PUT /api/v1/notifications/{id}/read – mark notification as read
     */
    @PutMapping("/{id}/read")
    public ResponseEntity<NotificationDTO> markRead(@PathVariable Long id,
                                                     Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        NotificationDTO dto = notificationService.markRead(userId, id);
        return ResponseEntity.ok(dto);
    }

    /**
     * PUT /api/v1/notifications/read-all – mark all as read
     */
    @PutMapping("/read-all")
    public ResponseEntity<Map<String, Integer>> markAllRead(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        int updated = notificationService.markAllRead(userId);
        return ResponseEntity.ok(Map.of("updated", updated));
    }

    /**
     * GET /api/v1/notifications/unread-count – get unread count
     */
    @GetMapping("/unread-count")
    public ResponseEntity<Map<String, Long>> getUnreadCount(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        long count = notificationService.getUnreadCount(userId);
        return ResponseEntity.ok(Map.of("unreadCount", count));
    }
}
