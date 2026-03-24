package com.health.physical.core.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.physical.common.entity.PhysicalRecord;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 体检记录Mapper
 */
@Mapper
public interface PhysicalRecordMapper extends BaseMapper<PhysicalRecord> {

    /**
     * 查询居民最新体检记录
     */
    PhysicalRecord selectLatestByResidentId(@Param("residentId") Long residentId);

    /**
     * 分页查询（含居民信息）
     */
    Page<PhysicalRecord> selectPageWithResident(Page<PhysicalRecord> page,
                                                  @Param("batchNo") String batchNo,
                                                  @Param("orgName") String orgName,
                                                  @Param("status") Integer status);

    /**
     * 查询待同步记录
     */
    List<PhysicalRecord> selectPendingSync(@Param("limit") int limit);
}
