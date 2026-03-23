package com.huidong.physical.sync.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.huidong.physical.common.entity.BaseEntity;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.time.LocalDateTime;

/**
 * 同步日志表
 * 记录每一条数据上报县域公卫平台的状态
 */
@Data
@EqualsAndHashCode(callSuper = true)
@TableName("t_sync_log")
public class SyncLog extends BaseEntity {

    /** 业务类型 EXAM=体检单 LAB=检验结果 */
    private String bizType;

    /** 业务ID */
    private Long bizId;

    /** 居民编码 */
    private String residentCode;

    /** 上报状态 0=待上报 1=成功 2=失败 3=重试中 4=耗尽 */
    private Integer syncStatus;

    /** 上报次数 */
    private Integer retryCount;

    /** 上次上报时间 */
    private LocalDateTime lastSyncTime;

    /** 下次重试时间 */
    private LocalDateTime nextRetryTime;

    /** 上报请求体（JSON） */
    private String requestBody;

    /** 上报响应体 */
    private String responseBody;

    /** 错误信息 */
    private String errorMsg;
}
