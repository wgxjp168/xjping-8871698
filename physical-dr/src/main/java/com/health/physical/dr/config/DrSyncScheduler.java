package com.health.physical.dr.config;

import com.health.physical.dr.service.DrService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * DR数据同步定时任务
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DrSyncScheduler {

    private final DrService drService;

    /**
     * 每5分钟批量同步DR结果至县域
     */
    @Scheduled(fixedDelay = 5 * 60 * 1000)
    public void batchSyncDrToCounty() {
        log.debug("[定时任务] 批量同步DR结果至县域公卫系统...");
        try {
            drService.batchSyncToCounty();
        } catch (Exception e) {
            log.error("[定时任务] DR批量同步异常: {}", e.getMessage(), e);
        }
    }
}
