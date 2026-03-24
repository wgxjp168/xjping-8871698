package com.health.physical.dr.service;

import com.health.physical.common.dto.PageResult;
import com.health.physical.dr.dto.DrScanRequest;
import com.health.physical.dr.dto.DrScanResponse;
import com.health.physical.dr.dto.DrSubmitRequest;
import com.health.physical.dr.entity.DrRecord;

/**
 * DR服务接口
 */
public interface DrService {

    /**
     * 扫描DR条码（院内技师扫码）
     * - 解析DR条码
     * - 带出居民信息和申请信息
     * - 校验DR操作权限
     * - 记录扫码时间
     */
    DrScanResponse scanDrBarcode(DrScanRequest request, String doctorId);

    /**
     * 提交DR检查结果
     * - 写入DR结果
     * - 更新状态为已完成
     * - 触发异步同步县域
     */
    void submitDrResult(DrSubmitRequest request, String doctorId);

    /**
     * 县域开单 - 在院内系统预注册DR条码
     * 当县域系统开单时，通过此接口在区域系统中创建待检查记录
     */
    DrRecord registerDrOrder(DrRecord drRecord);

    /**
     * 分页查询DR记录
     */
    PageResult<DrRecord> pageQuery(int current, int size, String batchNo, String examDoctorId,
                                    Integer status, String startDate, String endDate);

    /**
     * 查询DR记录详情
     */
    DrRecord getDetail(Long id);

    /**
     * 同步DR结果至县域公卫系统
     */
    void syncToCounty(Long drRecordId);

    /**
     * 批量同步待同步记录（定时任务调用）
     */
    void batchSyncToCounty();
}
