package com.health.physical.urine.service;

import com.health.physical.urine.entity.UrineResult;

import java.util.List;

/**
 * 尿机服务接口
 */
public interface UrineService {

    /**
     * 上传单条尿机结果（幂等：按条码去重）
     */
    UrineResult upload(UrineResult result);

    /**
     * 批量上传尿机结果（返回实际入库条数）
     */
    int batchUpload(List<UrineResult> results);

    /**
     * 查询体检单下的尿常规结果列表
     */
    List<UrineResult> getByPhysicalId(Long physicalId);

    /**
     * 按条码查询
     */
    UrineResult getByBarcode(String barcode);
}
