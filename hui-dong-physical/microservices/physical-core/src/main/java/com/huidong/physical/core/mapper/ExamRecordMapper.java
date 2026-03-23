package com.huidong.physical.core.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.huidong.physical.core.entity.ExamRecord;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 体检记录 Mapper
 */
@Mapper
public interface ExamRecordMapper extends BaseMapper<ExamRecord> {

    /**
     * 查询待同步的体检记录
     */
    List<ExamRecord> selectPendingSync(@Param("limit") int limit);

    /**
     * 按体检单号查询
     */
    ExamRecord selectByExamNo(@Param("examNo") String examNo);
}
