package com.huidong.physical.sync.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.huidong.physical.sync.entity.SyncLog;

import java.util.Map;

/**
 * 同步服务接口
 */
public interface SyncService extends IService<SyncLog> {

    /**
     * 同步体检单数据到县域公卫平台
     */
    void syncExamData(Long examRecordId, Map<String, Object> examData);

    /**
     * 同步检验结果到县域公卫平台
     */
    void syncLabResult(Long labResultId, Map<String, Object> labData);

    /**
     * 重试失败的同步任务（定时调用）
     */
    void retryFailed();
}
