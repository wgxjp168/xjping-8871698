package com.huidong.physical.sync.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.huidong.physical.sync.entity.SyncLog;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 同步日志 Mapper
 */
@Mapper
public interface SyncLogMapper extends BaseMapper<SyncLog> {

    /**
     * 查询需要重试的日志（状态=失败且重试次数未耗尽，且到达重试时间）
     */
    List<SyncLog> selectPendingRetry(@Param("now") LocalDateTime now, @Param("maxRetry") int maxRetry, @Param("limit") int limit);
}
