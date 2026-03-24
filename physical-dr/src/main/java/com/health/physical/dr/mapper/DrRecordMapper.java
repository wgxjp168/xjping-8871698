package com.health.physical.dr.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.physical.dr.entity.DrRecord;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * DR记录Mapper
 */
@Mapper
public interface DrRecordMapper extends BaseMapper<DrRecord> {

    /**
     * 按DR条码查询（含居民信息）
     */
    DrRecord selectByDrCode(@Param("drCode") String drCode);

    /**
     * 查询待同步县域的DR记录
     */
    List<DrRecord> selectPendingSync(@Param("limit") int limit);

    /**
     * 分页查询DR记录
     */
    Page<DrRecord> selectPageWithFilter(Page<DrRecord> page,
                                         @Param("batchNo") String batchNo,
                                         @Param("examDoctorId") String examDoctorId,
                                         @Param("status") Integer status,
                                         @Param("startDate") String startDate,
                                         @Param("endDate") String endDate);

    /**
     * 更新同步状态
     */
    int updateSyncStatus(@Param("id") Long id, @Param("syncTime") java.time.LocalDateTime syncTime);
}
