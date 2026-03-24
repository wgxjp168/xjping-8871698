package com.health.physical.core.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.physical.common.entity.PhysicalRecord;
import com.health.physical.core.entity.LabResult;

import java.util.List;

/**
 * 体检记录服务接口
 */
public interface PhysicalRecordService {

    /** 分页查询体检记录 */
    Page<PhysicalRecord> pageQuery(int current, int size, String batchNo, String orgName, Integer status);

    /** 查询体检记录详情 */
    PhysicalRecord getById(Long id);

    /** 查询体检单检验结果 */
    List<LabResult> getLabResults(Long physicalId, String projectCode);

    /** 新建体检记录 */
    PhysicalRecord create(PhysicalRecord record);

    /** 批量上传检验结果 */
    void uploadLabResults(Long physicalId, List<LabResult> results);

    /** 完成体检（状态2-已完成，触发同步） */
    void complete(Long id, String operatorDocId);
}
