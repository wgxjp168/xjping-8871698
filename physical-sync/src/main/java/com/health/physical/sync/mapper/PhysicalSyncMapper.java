package com.health.physical.sync.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.health.physical.common.entity.PhysicalRecord;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * 同步服务 - 体检记录Mapper
 */
@Mapper
public interface PhysicalSyncMapper extends BaseMapper<PhysicalRecord> {

    @Select("SELECT * FROM physical_record WHERE sync_status = 0 AND status = 2 AND deleted = 0 ORDER BY exam_date ASC LIMIT #{limit}")
    List<PhysicalRecord> selectPendingSync(@Param("limit") int limit);
}
