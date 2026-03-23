package com.huidong.physical.core.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.huidong.physical.core.entity.LabResult;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 检验结果 Mapper
 */
@Mapper
public interface LabResultMapper extends BaseMapper<LabResult> {

    /**
     * 查询体检单的所有检验结果
     */
    List<LabResult> selectByExamRecordId(@Param("examRecordId") Long examRecordId);

    /**
     * 查询待同步的检验结果
     */
    List<LabResult> selectPendingSync(@Param("limit") int limit);
}
