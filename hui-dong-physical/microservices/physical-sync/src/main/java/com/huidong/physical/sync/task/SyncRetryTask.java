package com.huidong.physical.sync.task;

import com.huidong.physical.sync.service.SyncService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 同步重试定时任务
 * 每5分钟扫描失败记录，按指数退避策略重试
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SyncRetryTask {

    private final SyncService syncService;

    @Scheduled(fixedDelay = 5 * 60 * 1000)
    public void retryFailedSync() {
        log.debug("开始执行同步重试任务");
        try {
            syncService.retryFailed();
        } catch (Exception e) {
            log.error("同步重试任务异常: {}", e.getMessage());
        }
    }
}
