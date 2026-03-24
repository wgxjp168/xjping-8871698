package com.health.physical.core.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.physical.common.entity.Resident;
import com.health.physical.common.exception.BusinessException;
import com.health.physical.core.mapper.ResidentMapper;
import com.health.physical.core.service.ResidentService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

/**
 * 居民信息服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ResidentServiceImpl implements ResidentService {

    private final ResidentMapper residentMapper;

    @Override
    public Resident getByIdCard(String idCard) {
        return residentMapper.selectByIdCard(idCard);
    }

    @Override
    public Page<Resident> pageQuery(int current, int size, String name, String village, String town) {
        Page<Resident> page = new Page<>(current, size);
        LambdaQueryWrapper<Resident> wrapper = new LambdaQueryWrapper<Resident>()
                .like(StringUtils.hasText(name), Resident::getName, name)
                .eq(StringUtils.hasText(village), Resident::getVillage, village)
                .eq(StringUtils.hasText(town), Resident::getTown, town)
                .eq(Resident::getStatus, 1)
                .orderByDesc(Resident::getCreateTime);
        return residentMapper.selectPage(page, wrapper);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Resident save(Resident resident) {
        // 检查身份证唯一性
        if (residentMapper.selectByIdCard(resident.getIdCard()) != null) {
            throw BusinessException.of("居民身份证已存在：" + resident.getIdCard());
        }
        resident.setStatus(1);
        resident.setDeleted(0);
        residentMapper.insert(resident);
        log.info("新增居民: idCard={}, name={}", resident.getIdCard(), resident.getName());
        return resident;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void update(Long id, Resident resident) {
        Resident existing = residentMapper.selectById(id);
        if (existing == null) {
            throw BusinessException.of("居民记录不存在：" + id);
        }
        resident.setId(id);
        residentMapper.updateById(resident);
        log.info("更新居民: id={}", id);
    }
}
