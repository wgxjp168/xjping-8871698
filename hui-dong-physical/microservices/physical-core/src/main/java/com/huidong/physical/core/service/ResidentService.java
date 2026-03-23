package com.huidong.physical.core.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.huidong.physical.core.entity.Resident;

/**
 * 居民信息服务接口
 */
public interface ResidentService extends IService<Resident> {

    /**
     * 按身份证号获取居民（优先缓存）
     */
    Resident getByIdCard(String idCard);

    /**
     * 按居民编码获取居民
     */
    Resident getByResidentCode(String residentCode);

    /**
     * 同步居民信息（从县域平台拉取）
     */
    Resident syncFromCountyPlatform(String residentCode);
}
