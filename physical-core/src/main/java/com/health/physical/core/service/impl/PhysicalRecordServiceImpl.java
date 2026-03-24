package com.health.physical.core.service.impl;

import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.physical.common.entity.PhysicalRecord;
import com.health.physical.common.exception.BusinessException;
import com.health.physical.core.entity.LabResult;
import com.health.physical.core.mapper.LabResultMapper;
import com.health.physical.core.mapper.PhysicalRecordMapper;
import com.health.physical.core.service.PhysicalRecordService;
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
public class PhysicalRecordServiceImpl implements PhysicalRecordService {

    private final PhysicalRecordMapper physicalRecordMapper;
    private final LabResultMapper labResultMapper;

    @Override
    public Page<PhysicalRecord> pageQuery(int current, int size, String batchNo, String orgName, Integer status) {
        Page<PhysicalRecord> page = new Page<>(current, size);
        physicalRecordMapper.selectPageWithResident(page, batchNo, orgName, status);
        return page;
    }

    @Override
    public PhysicalRecord getById(Long id) {
        PhysicalRecord record = physicalRecordMapper.selectById(id);
        if (record == null) {
            throw BusinessException.of("体检记录不存在：" + id);
        }
        return record;
    }

    @Override
    public List<LabResult> getLabResults(Long physicalId, String projectCode) {
        return labResultMapper.selectByPhysicalIdAndProject(physicalId, projectCode);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public PhysicalRecord create(PhysicalRecord record) {
        if (record.getExamDate() == null) {
            record.setExamDate(LocalDate.now());
        }
        record.setSyncStatus(0);
        record.setStatus(1);
        record.setDeleted(0);
        physicalRecordMapper.insert(record);
        log.info("新建体检记录: residentId={}, batchNo={}", record.getResidentId(), record.getBatchNo());
        return record;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void uploadLabResults(Long physicalId, List<LabResult> results) {
        if (results == null || results.isEmpty()) {
            return;
        }
        // 确认体检单存在
        PhysicalRecord record = physicalRecordMapper.selectById(physicalId);
        if (record == null) {
            throw BusinessException.of("体检记录不存在：" + physicalId);
        }
        results.forEach(r -> {
            r.setPhysicalId(physicalId);
            r.setResidentId(record.getResidentId());
            r.setSyncStatus(0);
            r.setStatus(1);
            r.setDeleted(0);
        });
        labResultMapper.batchInsertOrUpdate(results);
        log.info("上传检验结果: physicalId={}, count={}", physicalId, results.size());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void complete(Long id, String operatorDocId) {
        PhysicalRecord record = physicalRecordMapper.selectById(id);
        if (record == null) {
            throw BusinessException.of("体检记录不存在：" + id);
        }
        if (record.getStatus() == 2) {
            throw BusinessException.of("体检记录已完成，无需重复操作");
        }
        physicalRecordMapper.update(null, new LambdaUpdateWrapper<PhysicalRecord>()
                .eq(PhysicalRecord::getId, id)
                .set(PhysicalRecord::getStatus, 2)
                .set(PhysicalRecord::getOperator, operatorDocId));
        log.info("体检记录完成: id={}, operator={}", id, operatorDocId);
    }
}
