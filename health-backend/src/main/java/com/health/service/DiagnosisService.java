package com.health.service;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.common.PageResult;
import com.health.common.exception.BusinessException;
import com.health.dto.DiagnosisQueryDTO;
import com.health.dto.DiagnosisSaveDTO;
import com.health.entity.Diagnosis;
import com.health.mapper.DiagnosisMapper;
import com.health.vo.DiagnosisVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

/**
 * 诊断服务
 */
@Service
@RequiredArgsConstructor
public class DiagnosisService {

    private final DiagnosisMapper diagnosisMapper;

    public PageResult<DiagnosisVO> queryPage(DiagnosisQueryDTO query) {
        Page<DiagnosisVO> page = new Page<>(query.getPageNum(), query.getPageSize());
        diagnosisMapper.queryDiagnosisPage(page, query);
        return PageResult.of(page);
    }

    public DiagnosisVO getDetail(Long id) {
        DiagnosisVO vo = diagnosisMapper.getDiagnosisDetail(id);
        if (vo == null) {
            throw new BusinessException("诊断报告不存在");
        }
        return vo;
    }

    @Transactional
    public void save(DiagnosisSaveDTO dto, Long doctorId, Long patientId) {
        Diagnosis diagnosis;
        if (dto.getId() != null) {
            diagnosis = diagnosisMapper.selectById(dto.getId());
            if (diagnosis == null) {
                throw new BusinessException("诊断报告不存在");
            }
        } else {
            diagnosis = new Diagnosis();
            diagnosis.setStatus("DRAFT");
            diagnosis.setDoctorId(doctorId);
            diagnosis.setPatientId(patientId);
        }
        BeanUtil.copyProperties(dto, diagnosis, "id");
        if (dto.getId() != null) {
            diagnosis.setId(dto.getId());
        }
        if (dto.getRiskLevel() == null) {
            diagnosis.setRiskLevel("LOW");
        }
        if (diagnosis.getId() == null) {
            diagnosisMapper.insert(diagnosis);
        } else {
            diagnosisMapper.updateById(diagnosis);
        }
    }

    @Transactional
    public void confirm(Long id) {
        Diagnosis diagnosis = diagnosisMapper.selectById(id);
        if (diagnosis == null) {
            throw new BusinessException("诊断报告不存在");
        }
        diagnosis.setStatus("CONFIRMED");
        diagnosis.setConfirmTime(LocalDateTime.now());
        diagnosisMapper.updateById(diagnosis);
    }

    @Transactional
    public void publish(Long id) {
        Diagnosis diagnosis = diagnosisMapper.selectById(id);
        if (diagnosis == null) {
            throw new BusinessException("诊断报告不存在");
        }
        if (!"CONFIRMED".equals(diagnosis.getStatus())) {
            throw new BusinessException("请先确认诊断报告");
        }
        diagnosis.setStatus("PUBLISHED");
        diagnosis.setPublishTime(LocalDateTime.now());
        diagnosisMapper.updateById(diagnosis);
    }

    @Transactional
    public void delete(Long id) {
        diagnosisMapper.deleteById(id);
    }
}
