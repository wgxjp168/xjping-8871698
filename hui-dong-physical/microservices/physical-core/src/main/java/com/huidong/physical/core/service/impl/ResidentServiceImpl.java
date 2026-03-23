package com.huidong.physical.core.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.huidong.physical.common.exception.BusinessException;
import com.huidong.physical.common.result.ResultCode;
import com.huidong.physical.core.entity.Resident;
import com.huidong.physical.core.mapper.ResidentMapper;
import com.huidong.physical.core.service.ResidentService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

/**
 * 居民信息服务实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ResidentServiceImpl extends ServiceImpl<ResidentMapper, Resident> implements ResidentService {

    private final ResidentMapper residentMapper;
    private final StringRedisTemplate redisTemplate;

    private static final String RESIDENT_CACHE_KEY = "physical:resident:idcard:";
    private static final long CACHE_TTL_HOURS = 24;

    @Override
    public Resident getByIdCard(String idCard) {
        // 先查 Redis 缓存
        String cacheKey = RESIDENT_CACHE_KEY + idCard;
        String cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached != null) {
            log.debug("居民信息缓存命中: idCard={}", idCard);
            return com.alibaba.fastjson2.JSON.parseObject(cached, Resident.class);
        }

        // 查数据库
        Resident resident = residentMapper.selectByIdCard(idCard);
        if (resident == null) {
            throw new BusinessException(ResultCode.RESIDENT_NOT_FOUND);
        }

        // 写入缓存
        redisTemplate.opsForValue().set(cacheKey,
                com.alibaba.fastjson2.JSON.toJSONString(resident),
                CACHE_TTL_HOURS, TimeUnit.HOURS);
        return resident;
    }

    @Override
    public Resident getByResidentCode(String residentCode) {
        Resident resident = residentMapper.selectByResidentCode(residentCode);
        if (resident == null) {
            throw new BusinessException(ResultCode.RESIDENT_NOT_FOUND);
        }
        return resident;
    }

    @Override
    public Resident syncFromCountyPlatform(String residentCode) {
        // TODO: 调用县域公卫平台接口获取居民信息
        // 实际项目中通过 OpenFeign 或 RestTemplate 调用上级接口
        log.info("从县域平台同步居民信息: residentCode={}", residentCode);
        throw new UnsupportedOperationException("请配置县域公卫平台接口地址");
    }
}
