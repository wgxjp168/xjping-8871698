package com.health.physical.dr.service.impl;

import cn.hutool.core.util.IdUtil;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.physical.common.constant.PermissionConstants;
import com.health.physical.common.dto.PageResult;
import com.health.physical.common.exception.BusinessException;
import com.health.physical.dr.dto.DrScanRequest;
import com.health.physical.dr.dto.DrScanResponse;
import com.health.physical.dr.dto.DrSubmitRequest;
import com.health.physical.dr.entity.DrRecord;
import com.health.physical.dr.mapper.DrRecordMapper;
import com.health.physical.dr.service.DrService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RBucket;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * DR服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DrServiceImpl implements DrService {

    private final DrRecordMapper drRecordMapper;
    private final RedissonClient redissonClient;
    private final RestTemplate restTemplate;

    @Value("${auth.service.url:http://localhost:9005}")
    private String authServiceUrl;

    @Value("${county.api.base-url:http://county-gateway:8080}")
    private String countyApiUrl;

    @Value("${county.api.token:}")
    private String countyApiToken;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public DrScanResponse scanDrBarcode(DrScanRequest request, String doctorId) {
        String drCode = request.getDrCode().trim().toUpperCase();

        // 1. 查询DR记录
        DrRecord record = drRecordMapper.selectByDrCode(drCode);
        if (record == null) {
            throw BusinessException.of("DR条码不存在或已失效：" + drCode);
        }

        // 2. 状态校验
        if (record.getStatus() == 2 || record.getStatus() == 3) {
            return DrScanResponse.builder()
                    .id(record.getId())
                    .drCode(drCode)
                    .residentName(record.getResidentName())
                    .idCard(maskIdCard(record.getIdCard()))
                    .examPart(record.getExamPart())
                    .statusDesc(record.getStatus() == 2 ? "已完成检查" : "已上传县域")
                    .canExam(0)
                    .cannotReason("该DR条码对应的检查已完成，不可重复检查")
                    .scanTime(LocalDateTime.now())
                    .build();
        }
        if (record.getStatus() == 4) {
            return DrScanResponse.builder()
                    .id(record.getId())
                    .drCode(drCode)
                    .residentName(record.getResidentName())
                    .canExam(0)
                    .cannotReason("该DR申请已取消")
                    .scanTime(LocalDateTime.now())
                    .build();
        }

        // 3. 记录扫码信息，更新状态为检查中
        drRecordMapper.update(null, new LambdaUpdateWrapper<DrRecord>()
                .eq(DrRecord::getId, record.getId())
                .set(DrRecord::getScanOperator, doctorId)
                .set(DrRecord::getScanTime, LocalDateTime.now())
                .set(DrRecord::getStatus, 1));

        // 4. 缓存DR操作记录（防止重复扫码）
        String cacheKey = "physical:dr:scan:" + drCode;
        RBucket<String> bucket = redissonClient.getBucket(cacheKey);
        bucket.set(doctorId, 30, TimeUnit.MINUTES);

        log.info("DR条码扫描成功: drCode={}, residentName={}, doctor={}", drCode, record.getResidentName(), doctorId);

        return DrScanResponse.builder()
                .id(record.getId())
                .drCode(drCode)
                .applyNo(record.getApplyNo())
                .residentId(record.getResidentId())
                .residentName(record.getResidentName())
                .idCard(maskIdCard(record.getIdCard()))
                .examPart(record.getExamPart())
                .statusDesc("待检查")
                .canExam(1)
                .scanTime(LocalDateTime.now())
                .build();
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void submitDrResult(DrSubmitRequest request, String doctorId) {
        // 1. 校验记录存在
        DrRecord record = drRecordMapper.selectById(request.getId());
        if (record == null) {
            throw BusinessException.of("DR记录不存在");
        }
        if (record.getStatus() == 2 || record.getStatus() == 3) {
            throw BusinessException.of("DR记录已完成，不可重复提交");
        }

        // 2. 更新DR检查结果
        drRecordMapper.update(null, new LambdaUpdateWrapper<DrRecord>()
                .eq(DrRecord::getId, request.getId())
                .set(DrRecord::getDrResult, request.getDrResult())
                .set(DrRecord::getConclusion, request.getConclusion())
                .set(DrRecord::getExamDoctorId, request.getExamDoctorId())
                .set(DrRecord::getExamDoctor, request.getExamDoctor())
                .set(DrRecord::getExamTime, LocalDateTime.now())
                .set(DrRecord::getImagePath, request.getImagePath())
                .set(DrRecord::getRemark, request.getRemark())
                .set(DrRecord::getStatus, 2));

        log.info("DR检查结果提交成功: id={}, drCode={}, doctor={}", request.getId(), request.getDrCode(), doctorId);

        // 3. 异步同步至县域公卫系统
        asyncSyncToCounty(request.getId());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public DrRecord registerDrOrder(DrRecord drRecord) {
        // 校验DR条码是否已存在
        if (drRecord.getDrCode() != null) {
            DrRecord existing = drRecordMapper.selectByDrCode(drRecord.getDrCode());
            if (existing != null) {
                log.warn("DR条码已存在，跳过注册: drCode={}", drRecord.getDrCode());
                return existing;
            }
        } else {
            // 本地生成DR条码（正常应由县域系统生成并传入）
            drRecord.setDrCode("DR" + IdUtil.getSnowflakeNextIdStr());
        }

        drRecord.setStatus(0); // 待检查
        drRecordMapper.insert(drRecord);
        log.info("DR开单注册成功: drCode={}, residentId={}", drRecord.getDrCode(), drRecord.getResidentId());
        return drRecord;
    }

    @Override
    public PageResult<DrRecord> pageQuery(int current, int size, String batchNo, String examDoctorId,
                                           Integer status, String startDate, String endDate) {
        Page<DrRecord> page = new Page<>(current, size);
        drRecordMapper.selectPageWithFilter(page, batchNo, examDoctorId, status, startDate, endDate);
        return PageResult.of(page);
    }

    @Override
    public DrRecord getDetail(Long id) {
        DrRecord record = drRecordMapper.selectById(id);
        if (record == null) {
            throw BusinessException.of("DR记录不存在");
        }
        return record;
    }

    @Override
    public void syncToCounty(Long drRecordId) {
        DrRecord record = drRecordMapper.selectById(drRecordId);
        if (record == null || record.getStatus() != 2) {
            return;
        }
        try {
            // 调用县域公卫系统接口同步DR结果
            // TODO: 实际实现需按照县域系统接口文档组装请求
            log.info("同步DR结果至县域公卫系统: drCode={}, conclusion={}", record.getDrCode(), record.getConclusion());

            // 更新同步状态
            drRecordMapper.updateSyncStatus(drRecordId, LocalDateTime.now());
            log.info("DR结果同步县域成功: id={}, drCode={}", drRecordId, record.getDrCode());
        } catch (Exception e) {
            log.error("DR结果同步县域失败: id={}, error={}", drRecordId, e.getMessage(), e);
        }
    }

    @Override
    public void batchSyncToCounty() {
        List<DrRecord> pendingList = drRecordMapper.selectPendingSync(50);
        log.info("批量同步DR结果至县域，共{}条", pendingList.size());
        for (DrRecord record : pendingList) {
            try {
                syncToCounty(record.getId());
            } catch (Exception e) {
                log.error("DR批量同步失败: id={}, error={}", record.getId(), e.getMessage());
            }
        }
    }

    @Async
    public void asyncSyncToCounty(Long drRecordId) {
        syncToCounty(drRecordId);
    }

    /** 身份证脱敏：保留前6位和后4位 */
    private String maskIdCard(String idCard) {
        if (idCard == null || idCard.length() < 11) return idCard;
        return idCard.substring(0, 6) + "********" + idCard.substring(idCard.length() - 4);
    }
}
