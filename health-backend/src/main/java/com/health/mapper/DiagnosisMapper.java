package com.health.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.dto.DiagnosisQueryDTO;
import com.health.entity.Diagnosis;
import com.health.vo.DiagnosisVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 诊断报告 Mapper
 */
@Mapper
public interface DiagnosisMapper extends BaseMapper<Diagnosis> {

    Page<DiagnosisVO> queryDiagnosisPage(Page<DiagnosisVO> page, @Param("query") DiagnosisQueryDTO query);

    DiagnosisVO getDiagnosisDetail(@Param("id") Long id);
}
