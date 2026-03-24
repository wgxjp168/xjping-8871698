package com.health.physical.urine.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.health.physical.urine.entity.UrineResult;
import com.health.physical.urine.mapper.UrineResultMapper;
import com.health.physical.urine.service.UrineService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 尿机服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class UrineServiceImpl implements UrineService {

    private final UrineResultMapper urineResultMapper;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public UrineResult upload(UrineResult result) {
        // 幂等检查：同一条码只保存一次
        UrineResult existing = getByBarcode(result.getBarcode());
        if (existing != null) {
            log.warn("[UrineService] 尿机结果已存在，忽略重复上传: barcode={}", result.getBarcode());
            return existing;
        }
        result.setUploadTime(LocalDateTime.now());
        result.setSyncStatus(0);
        result.setStatus(1);
        result.setDeleted(0);
        urineResultMapper.insert(result);
        log.info("[UrineService] 尿机结果上传成功: barcode={}, residentId={}", result.getBarcode(), result.getResidentId());
        return result;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public int batchUpload(List<UrineResult> results) {
        int success = 0;
        for (UrineResult result : results) {
            try {
                UrineResult uploaded = upload(result);
                // 若 uploaded 的 uploadTime 等于刚刚设置的时间，说明是新增的
                if (uploaded.getId() != null && result.getId() == null) {
                    success++;
                }
            } catch (Exception e) {
                log.error("[UrineService] 批量上传单条失败: barcode={}, error={}", result.getBarcode(), e.getMessage());
            }
        }
        log.info("[UrineService] 批量上传完成: total={}, success={}", results.size(), success);
        return success;
    }

    @Override
    public List<UrineResult> getByPhysicalId(Long physicalId) {
        return urineResultMapper.selectList(
                new LambdaQueryWrapper<UrineResult>()
                        .eq(UrineResult::getPhysicalId, physicalId)
                        .eq(UrineResult::getDeleted, 0)
                        .orderByDesc(UrineResult::getCollectTime)
        );
    }

    @Override
    public UrineResult getByBarcode(String barcode) {
        return urineResultMapper.selectOne(
                new LambdaQueryWrapper<UrineResult>()
                        .eq(UrineResult::getBarcode, barcode)
                        .eq(UrineResult::getDeleted, 0)
        );
    }
}
