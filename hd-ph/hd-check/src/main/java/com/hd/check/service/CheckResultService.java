package com.hd.check.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.hd.check.entity.CheckResult;
import com.hd.check.mapper.CheckResultMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class CheckResultService {

    @Autowired
    private CheckResultMapper resultMapper;

    public List<CheckResult> listByOrder(Long orderId) {
        return resultMapper.selectList(
                new LambdaQueryWrapper<CheckResult>()
                        .eq(CheckResult::getOrderId, orderId)
                        .eq(CheckResult::getDeleted, 0)
                        .orderByAsc(CheckResult::getCategory, CheckResult::getItemCode)
        );
    }

    public List<CheckResult> listByOrderAndCategory(Long orderId, String category) {
        return resultMapper.selectList(
                new LambdaQueryWrapper<CheckResult>()
                        .eq(CheckResult::getOrderId, orderId)
                        .eq(CheckResult::getCategory, category)
                        .eq(CheckResult::getDeleted, 0)
        );
    }

    public List<CheckResult> listByResident(Long residentId) {
        return resultMapper.selectList(
                new LambdaQueryWrapper<CheckResult>()
                        .eq(CheckResult::getResidentId, residentId)
                        .eq(CheckResult::getDeleted, 0)
                        .orderByDesc(CheckResult::getCreateTime)
        );
    }

    @Transactional
    public void saveResults(List<CheckResult> results) {
        for (CheckResult result : results) {
            resultMapper.insert(result);
        }
    }

    @Transactional
    public void saveOrUpdate(CheckResult result) {
        if (result.getId() == null) {
            resultMapper.insert(result);
        } else {
            resultMapper.updateById(result);
        }
    }

    public void delete(Long id) {
        CheckResult r = new CheckResult();
        r.setId(id);
        r.setDeleted(1);
        resultMapper.updateById(r);
    }
}
