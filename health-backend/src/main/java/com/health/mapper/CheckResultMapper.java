package com.health.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.health.entity.CheckResult;
import com.health.vo.CheckResultVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 体检结果 Mapper
 */
@Mapper
public interface CheckResultMapper extends BaseMapper<CheckResult> {

    List<CheckResultVO> getResultsByOrderId(@Param("orderId") Long orderId);
}
