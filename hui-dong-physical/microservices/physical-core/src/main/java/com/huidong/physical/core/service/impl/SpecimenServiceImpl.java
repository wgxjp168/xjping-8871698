package com.huidong.physical.core.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.huidong.physical.common.exception.BusinessException;
import com.huidong.physical.common.result.ResultCode;
import com.huidong.physical.core.entity.Specimen;
import com.huidong.physical.core.mapper.SpecimenMapper;
import com.huidong.physical.core.service.SpecimenService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 标本服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SpecimenServiceImpl extends ServiceImpl<SpecimenMapper, Specimen> implements SpecimenService {

    private final SpecimenMapper specimenMapper;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Specimen bindSpecimenToExam(String barcodeNo, Long examRecordId) {
        Specimen existing = specimenMapper.selectByBarcodeNo(barcodeNo);
        if (existing != null && existing.getExamRecordId() != null) {
            throw new BusinessException(ResultCode.DUPLICATE_SPECIMEN);
        }

        if (existing == null) {
            existing = new Specimen();
            existing.setBarcodeNo(barcodeNo);
        }
        existing.setExamRecordId(examRecordId);
        existing.setSpecimenStatus(1); // 检验中
        saveOrUpdate(existing);
        log.info("标本关联体检单: barcodeNo={}, examRecordId={}", barcodeNo, examRecordId);
        return existing;
    }

    @Override
    public Specimen getByBarcodeNo(String barcodeNo) {
        Specimen specimen = specimenMapper.selectByBarcodeNo(barcodeNo);
        if (specimen == null) {
            throw new BusinessException(ResultCode.SPECIMEN_NOT_FOUND);
        }
        return specimen;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void completeSpecimen(Long specimenId) {
        Specimen specimen = getById(specimenId);
        if (specimen == null) {
            throw new BusinessException(ResultCode.SPECIMEN_NOT_FOUND);
        }
        specimen.setSpecimenStatus(2); // 已完成
        updateById(specimen);
    }
}
