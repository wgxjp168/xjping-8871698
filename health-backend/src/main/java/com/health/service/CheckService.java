package com.health.service;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.date.DateUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.health.common.PageResult;
import com.health.common.exception.BusinessException;
import com.health.dto.CheckOrderQueryDTO;
import com.health.dto.CheckResultSaveDTO;
import com.health.entity.CheckItem;
import com.health.entity.CheckOrder;
import com.health.entity.CheckResult;
import com.health.mapper.CheckItemMapper;
import com.health.mapper.CheckOrderMapper;
import com.health.mapper.CheckResultMapper;
import com.health.vo.CheckOrderVO;
import com.health.vo.CheckResultVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 体检服务
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class CheckService {

    private final CheckOrderMapper checkOrderMapper;
    private final CheckResultMapper checkResultMapper;
    private final CheckItemMapper checkItemMapper;

    public PageResult<CheckOrderVO> queryOrderPage(CheckOrderQueryDTO query) {
        Page<CheckOrderVO> page = new Page<>(query.getPageNum(), query.getPageSize());
        checkOrderMapper.queryOrderPage(page, query);
        return PageResult.of(page);
    }

    public CheckOrderVO getOrderDetail(Long orderId) {
        CheckOrderVO order = checkOrderMapper.getOrderDetail(orderId);
        if (order == null) {
            throw new BusinessException("体检单不存在");
        }
        List<CheckResultVO> results = checkResultMapper.getResultsByOrderId(orderId);
        order.setResults(results);
        return order;
    }

    @Transactional
    public CheckOrder createOrder(Long patientId, Long packageId) {
        CheckOrder order = new CheckOrder();
        order.setOrderNo(generateOrderNo());
        order.setPatientId(patientId);
        order.setPackageId(packageId);
        order.setCheckDate(LocalDate.now());
        order.setStatus("CREATED");
        checkOrderMapper.insert(order);
        return order;
    }

    @Transactional
    public void updateOrderStatus(Long orderId, String status) {
        CheckOrder order = checkOrderMapper.selectById(orderId);
        if (order == null) {
            throw new BusinessException("体检单不存在");
        }
        order.setStatus(status);
        checkOrderMapper.updateById(order);
    }

    @Transactional
    public void saveResult(CheckResultSaveDTO dto) {
        CheckItem item = checkItemMapper.selectById(dto.getItemId());
        if (item == null) {
            throw new BusinessException("检查项不存在");
        }

        CheckResult result;
        if (dto.getId() != null) {
            result = checkResultMapper.selectById(dto.getId());
            if (result == null) {
                throw new BusinessException("结果记录不存在");
            }
        } else {
            result = new CheckResult();
        }

        BeanUtil.copyProperties(dto, result);
        result.setItemName(item.getName());
        result.setUnit(item.getUnit());
        result.setNormalRange(item.getNormalText());
        if (result.getCheckTime() == null) {
            result.setCheckTime(LocalDateTime.now());
        }
        if (dto.getDataSource() == null) {
            result.setDataSource("MANUAL");
        }

        // 自动判断标记
        if (item.getNormalMin() != null && item.getNormalMax() != null) {
            try {
                double val = Double.parseDouble(dto.getValue());
                if (val < item.getNormalMin().doubleValue()) {
                    result.setFlag("LOW");
                } else if (val > item.getNormalMax().doubleValue()) {
                    result.setFlag("HIGH");
                } else {
                    result.setFlag("NORMAL");
                }
            } catch (NumberFormatException ignored) {
                result.setFlag("NORMAL");
            }
        }

        if (result.getId() == null) {
            checkResultMapper.insert(result);
        } else {
            checkResultMapper.updateById(result);
        }

        // 检查是否所有项目已完成，自动更新状态
        updateOrderStatusIfComplete(dto.getOrderId());
    }

    private void updateOrderStatusIfComplete(Long orderId) {
        CheckOrder order = checkOrderMapper.selectById(orderId);
        if (order != null && "CREATED".equals(order.getStatus())) {
            order.setStatus("IN_PROGRESS");
            checkOrderMapper.updateById(order);
        }
    }

    private String generateOrderNo() {
        return "HC" + DateUtil.format(java.util.Date.from(
                LocalDateTime.now().atZone(java.time.ZoneId.systemDefault()).toInstant()), "yyyyMMddHHmmss")
                + String.format("%04d", (int)(Math.random() * 10000));
    }

    public List<CheckResultVO> getResultsByOrderId(Long orderId) {
        return checkResultMapper.getResultsByOrderId(orderId);
    }
}
