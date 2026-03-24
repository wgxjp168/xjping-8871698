package com.health.physical.core.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.physical.common.entity.Resident;

/**
 * 居民信息服务接口
 */
public interface ResidentService {

    /** 按身份证查询居民 */
    Resident getByIdCard(String idCard);

    /** 分页查询居民 */
    Page<Resident> pageQuery(int current, int size, String name, String village, String town);

    /** 新增居民（检查身份证唯一性） */
    Resident save(Resident resident);

    /** 更新居民信息 */
    void update(Long id, Resident resident);
}
