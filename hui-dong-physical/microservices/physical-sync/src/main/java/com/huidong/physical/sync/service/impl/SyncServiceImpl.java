package com.huidong.physical.sync.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.huidong.physical.sync.entity.SyncLog;
import com.huidong.physical.sync.mapper.SyncLogMapper;
import com.huidong.physical.sync.service.CountyPlatformClient;
import com.huidong.physical.sync.service.SyncService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 同步服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SyncServiceImpl extends ServiceImpl<SyncLogMapper, SyncLog> implements SyncService {

    private static final int MAX_RETRY = 5;
    private static final int[] RETRY_DELAY_MINUTES = {1, 3, 10, 30, 60};

    private final SyncLogMapper syncLogMapper;
    private final CountyPlatformClient platformClient;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void syncExamData(Long examRecordId, Map<String, Object> examData) {
        SyncLog log = createSyncLog("EXAM", examRecordId, examData);
        save(log);
        doSync(log, examData, false);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void syncLabResult(Long labResultId, Map<String, Object> labData) {
        SyncLog log = createSyncLog("LAB", labResultId, labData);
        save(log);
        doSync(log, labData, true);
    }

    @Override
    public void retryFailed() {
        java.util.List<SyncLog> failedLogs = syncLogMapper.selectPendingRetry(
                LocalDateTime.now(), MAX_RETRY, 50);

        for (SyncLog syncLog : failedLogs) {
            java.util.Map<String, Object> data = com.alibaba.fastjson2.JSON.parseObject(
                    syncLog.getRequestBody(), java.util.Map.class);
            doSync(syncLog, data, "LAB".equals(syncLog.getBizType()));
        }
        log.info("重试同步完成: count={}", failedLogs.size());
    }

    private void doSync(SyncLog syncLog, Map<String, Object> data, boolean isLab) {
        boolean success;
        try {
            success = isLab
                    ? platformClient.reportLabResult(data)
                    : platformClient.reportExamData(data);
        } catch (Exception e) {
            success = false;
            syncLog.setErrorMsg(e.getMessage());
        }

        syncLog.setLastSyncTime(LocalDateTime.now());
        syncLog.setRetryCount(syncLog.getRetryCount() + 1);

        if (success) {
            syncLog.setSyncStatus(1);
            syncLog.setNextRetryTime(null);
            log.info("同步成功: bizType={}, bizId={}", syncLog.getBizType(), syncLog.getBizId());
        } else {
            int retryCount = syncLog.getRetryCount();
            if (retryCount >= MAX_RETRY) {
                syncLog.setSyncStatus(4); // 重试耗尽
                log.warn("同步重试耗尽: bizType={}, bizId={}", syncLog.getBizType(), syncLog.getBizId());
            } else {
                syncLog.setSyncStatus(2); // 失败，等待重试
                int delayMinutes = RETRY_DELAY_MINUTES[Math.min(retryCount, RETRY_DELAY_MINUTES.length - 1)];
                syncLog.setNextRetryTime(LocalDateTime.now().plusMinutes(delayMinutes));
            }
        }
        updateById(syncLog);
    }

    private SyncLog createSyncLog(String bizType, Long bizId, Map<String, Object> data) {
        SyncLog log = new SyncLog();
        log.setBizType(bizType);
        log.setBizId(bizId);
        log.setSyncStatus(0);
        log.setRetryCount(0);
        log.setRequestBody(com.alibaba.fastjson2.JSON.toJSONString(data));
        return log;
    }
}
