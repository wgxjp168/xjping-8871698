package com.huidong.physical.core.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.huidong.physical.common.enums.ExamStatusEnum;
import com.huidong.physical.common.exception.BusinessException;
import com.huidong.physical.common.result.ResultCode;
import com.huidong.physical.common.utils.IdUtils;
import com.huidong.physical.core.dto.CreateExamRecordDTO;
import com.huidong.physical.core.dto.ExamRecordVO;
import com.huidong.physical.core.entity.ExamRecord;
import com.huidong.physical.core.entity.LabResult;
import com.huidong.physical.core.entity.Resident;
import com.huidong.physical.core.entity.Specimen;
import com.huidong.physical.core.mapper.ExamRecordMapper;
import com.huidong.physical.core.mapper.LabResultMapper;
import com.huidong.physical.core.mapper.SpecimenMapper;
import com.huidong.physical.core.service.ExamRecordService;
import com.huidong.physical.core.service.ResidentService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;

/**
 * 体检记录服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ExamRecordServiceImpl extends ServiceImpl<ExamRecordMapper, ExamRecord> implements ExamRecordService {

    private final ExamRecordMapper examRecordMapper;
    private final SpecimenMapper specimenMapper;
    private final LabResultMapper labResultMapper;
    private final ResidentService residentService;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public ExamRecord createExamRecord(CreateExamRecordDTO dto) {
        // 获取居民信息
        Resident resident;
        if (dto.getIdentifierType() == 1) {
            resident = residentService.getByResidentCode(dto.getResidentIdentifier());
        } else {
            resident = residentService.getByIdCard(dto.getResidentIdentifier());
        }

        ExamRecord record = new ExamRecord();
        record.setExamNo(IdUtils.generateExamNo());
        record.setResidentId(resident.getId());
        record.setResidentCode(resident.getResidentCode());
        record.setExamType(dto.getExamType());
        record.setExamDate(dto.getExamDate() != null ? dto.getExamDate() : LocalDate.now());
        record.setExamLocation(dto.getExamLocation());
        record.setExamStatus(ExamStatusEnum.PENDING.getCode());
        record.setSyncStatus(0);

        save(record);
        log.info("创建体检单成功: examNo={}, residentCode={}", record.getExamNo(), resident.getResidentCode());
        return record;
    }

    @Override
    public ExamRecordVO getExamDetail(String examNo) {
        ExamRecord record = examRecordMapper.selectByExamNo(examNo);
        if (record == null) {
            throw new BusinessException(ResultCode.EXAM_RECORD_NOT_FOUND);
        }

        Resident resident = residentService.getById(record.getResidentId());
        List<Specimen> specimens = specimenMapper.selectByExamRecordId(record.getId());
        List<LabResult> labResults = labResultMapper.selectByExamRecordId(record.getId());

        ExamRecordVO vo = new ExamRecordVO();
        vo.setExamRecord(record);
        vo.setResidentName(resident != null ? resident.getName() : "");
        vo.setIdCard(resident != null ? maskIdCard(resident.getIdCard()) : "");
        vo.setSpecimens(specimens);
        vo.setLabResults(labResults);
        return vo;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void receiveLabResult(Long examRecordId, String labType) {
        ExamRecord record = getById(examRecordId);
        if (record == null) {
            throw new BusinessException(ResultCode.EXAM_RECORD_NOT_FOUND);
        }
        // 更新状态为检验中
        if (ExamStatusEnum.PENDING.getCode().equals(record.getExamStatus())
                || ExamStatusEnum.SPECIMEN_COLLECTED.getCode().equals(record.getExamStatus())) {
            record.setExamStatus(ExamStatusEnum.LAB_TESTING.getCode());
            updateById(record);
        }
        log.info("体检单收到检验结果: examRecordId={}, labType={}", examRecordId, labType);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void completeExam(String examNo) {
        ExamRecord record = examRecordMapper.selectByExamNo(examNo);
        if (record == null) {
            throw new BusinessException(ResultCode.EXAM_RECORD_NOT_FOUND);
        }
        record.setExamStatus(ExamStatusEnum.COMPLETED.getCode());
        updateById(record);
        log.info("体检单完成: examNo={}", examNo);
    }

    /** 身份证脱敏 */
    private String maskIdCard(String idCard) {
        if (idCard == null || idCard.length() < 6) return idCard;
        return idCard.substring(0, 3) + "***********" + idCard.substring(idCard.length() - 3);
    }
}
