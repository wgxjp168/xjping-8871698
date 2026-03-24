package com.health.physical.auth.config;

import com.health.physical.auth.service.AuthService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * 县域公卫系统同步定时任务
 * 每日凌晨1点同步医生账号和权限
 */
@Slf4j
@Component
@EnableScheduling
@RequiredArgsConstructor
public class CountySyncScheduler {

    private final AuthService authService;

    /**
     * 每日凌晨1:00同步县域医生账号和权限
     */
    @Scheduled(cron = "0 0 1 * * ?")
    public void syncDoctorsFromCounty() {
        log.info("[定时任务] 开始同步县域公卫系统医生账号和权限...");
        try {
            authService.syncFromCounty();
            log.info("[定时任务] 县域同步完成");
        } catch (Exception e) {
            log.error("[定时任务] 县域同步失败: {}", e.getMessage(), e);
        }
    }
}
