package com.hd.dr.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.hd.dr.entity.DrOrder;
import com.hd.dr.mapper.DrOrderMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Service
public class DrOrderService {

    @Autowired
    private DrOrderMapper orderMapper;

    public IPage<DrOrder> page(int current, int size, String residentName, String idCard,
                                Integer status, Long applyDeptId) {
        Page<DrOrder> pageParam = new Page<>(current, size);
        return orderMapper.selectOrderPage(pageParam, residentName, idCard, status, applyDeptId);
    }

    public DrOrder getById(Long id) {
        return orderMapper.selectById(id);
    }

    public DrOrder getByBarcodeNo(String barcodeNo) {
        return orderMapper.selectOne(
                new LambdaQueryWrapper<DrOrder>()
                        .eq(DrOrder::getBarcodeNo, barcodeNo)
                        .eq(DrOrder::getDeleted, 0)
        );
    }

    public void create(DrOrder order) {
        if (order.getDrOrderNo() == null || order.getDrOrderNo().isEmpty()) {
            order.setDrOrderNo(generateOrderNo());
        }
        if (order.getBarcodeNo() == null || order.getBarcodeNo().isEmpty()) {
            order.setBarcodeNo(generateBarcodeNo());
        }
        order.setStatus(0);
        order.setApplyTime(LocalDateTime.now());
        orderMapper.insert(order);
    }

    /**
     * 扫码签到（根据条码号查找申请单并更新状态）
     */
    public DrOrder scanBarcode(String barcodeNo, Long scanUserId) {
        DrOrder order = getByBarcodeNo(barcodeNo);
        if (order == null) {
            throw new RuntimeException("条码不存在: " + barcodeNo);
        }
        if (order.getStatus() != 0) {
            throw new RuntimeException("该申请单已扫码或已完成，状态: " + order.getStatus());
        }
        order.setStatus(1);
        order.setScanTime(LocalDateTime.now());
        order.setScanUserId(scanUserId);
        orderMapper.updateById(order);
        return order;
    }

    public void updateStatus(Long id, Integer status) {
        DrOrder order = new DrOrder();
        order.setId(id);
        order.setStatus(status);
        if (status == 2) {
            order.setFinishTime(LocalDateTime.now());
        }
        orderMapper.updateById(order);
    }

    public long countThisMonth() {
        LocalDate now = LocalDate.now();
        LocalDateTime monthStart = now.withDayOfMonth(1).atStartOfDay();
        LocalDateTime monthEnd = now.plusMonths(1).withDayOfMonth(1).atStartOfDay();
        return orderMapper.selectCount(
                new LambdaQueryWrapper<DrOrder>()
                        .ge(DrOrder::getCreateTime, monthStart)
                        .lt(DrOrder::getCreateTime, monthEnd)
                        .eq(DrOrder::getDeleted, 0)
        );
    }

    public void delete(Long id) {
        DrOrder order = new DrOrder();
        order.setId(id);
        order.setDeleted(1);
        orderMapper.updateById(order);
    }

    private String generateOrderNo() {
        return "DR" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + String.format("%03d", (int)(Math.random() * 999 + 1));
    }

    private String generateBarcodeNo() {
        return "BC" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + String.format("%04d", (int)(Math.random() * 9999 + 1));
    }
}
