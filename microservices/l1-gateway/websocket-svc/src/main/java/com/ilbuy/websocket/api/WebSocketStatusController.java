package com.ilbuy.websocket.api;

import com.ilbuy.common.core.result.Result;
import com.ilbuy.websocket.dto.SessionInfo;
import com.ilbuy.websocket.service.SessionManagerService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.Optional;

/**
 * WebSocket 会话状态 REST API
 *
 * <p>提供给运维监控、网关及其他内部服务查询 WS 会话状态。
 *
 * @author ILbuy Team
 */
@RestController
@RequestMapping("/ws/status")
@RequiredArgsConstructor
@Tag(name = "WebSocket状态接口", description = "查询在线人数/会话信息（内部接口）")
public class WebSocketStatusController {

    private final SessionManagerService sessionManager;

    /**
     * 获取当前在线连接数
     */
    @GetMapping("/online-count")
    @Operation(summary = "获取在线连接数")
    public Result<Map<String, Integer>> getOnlineCount() {
        return Result.ok(Map.of("onlineCount", sessionManager.getOnlineCount()));
    }

    /**
     * 查询指定 WS Session 信息
     */
    @GetMapping("/session/{wsSessionId}")
    @Operation(summary = "查询会话信息")
    public Result<SessionInfo> getSession(@PathVariable String wsSessionId) {
        Optional<SessionInfo> info = sessionManager.getSessionInfo(wsSessionId);
        return info.map(Result::ok).orElse(Result.notFound("会话不存在"));
    }

    /**
     * 向指定用户推送系统消息（运维/通知服务调用）
     */
    @PostMapping("/push/{userId}")
    @Operation(summary = "推送系统消息给指定用户")
    public Result<Map<String, Integer>> pushToUser(
            @PathVariable String userId,
            @RequestBody String message) {
        int count = sessionManager.pushToUser(userId, message);
        return Result.ok(Map.of("deliveredCount", count));
    }
}
