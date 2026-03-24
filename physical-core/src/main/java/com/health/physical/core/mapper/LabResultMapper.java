package com.health.physical.core.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.health.physical.core.entity.LabResult;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 检验结果Mapper
 */
@Mapper
public interface LabResultMapper extends BaseMapper<LabResult> {

    /**
     * 按体检单ID+项目编码查询检验结果
     */
    List<LabResult> selectByPhysicalIdAndProject(@Param("physicalId") Long physicalId,
                                                  @Param("projectCode") String projectCode);

    /**
     * 批量插入或更新检验结果
     */
    int batchInsertOrUpdate(@Param("list") List<LabResult> list);
}
