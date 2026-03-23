package com.huidong.physical.core.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.huidong.physical.core.entity.Specimen;

/**
 * 标本服务接口
 */
public interface SpecimenService extends IService<Specimen> {

    /**
     * 院内扫码关联居民：扫标本条码，关联到体检单
     */
    Specimen bindSpecimenToExam(String barcodeNo, Long examRecordId);

    /**
     * 按条码查标本
     */
    Specimen getByBarcodeNo(String barcodeNo);

    /**
     * 标本完成检验
     */
    void completeSpecimen(Long specimenId);
}
