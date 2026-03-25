package com.hd.check.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hd.check.entity.VitalSign;
import com.hd.check.mapper.VitalSignMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;

@Service
public class VitalSignService {

    @Autowired
    private VitalSignMapper vitalSignMapper;

    public VitalSign getByOrder(Long orderId) {
        return vitalSignMapper.selectOne(
                new LambdaQueryWrapper<VitalSign>()
                        .eq(VitalSign::getOrderId, orderId)
                        .eq(VitalSign::getDeleted, 0)
        );
    }

    public void saveOrUpdate(VitalSign vital) {
        // 自动计算 BMI
        if (vital.getHeight() != null && vital.getWeight() != null
                && vital.getHeight().compareTo(BigDecimal.ZERO) > 0) {
            BigDecimal heightM = vital.getHeight().divide(new BigDecimal("100"), 2, RoundingMode.HALF_UP);
            BigDecimal bmi = vital.getWeight().divide(heightM.multiply(heightM), 1, RoundingMode.HALF_UP);
            vital.setBmi(bmi);
        }
        VitalSign existing = getByOrder(vital.getOrderId());
        if (existing != null) {
            vital.setId(existing.getId());
            vitalSignMapper.updateById(vital);
        } else {
            vitalSignMapper.insert(vital);
        }
    }
}
