package com.hd.check.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.hd.check.entity.CheckOrder;
import com.hd.check.mapper.CheckOrderMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

@Service
public class CheckOrderService {

    @Autowired
    private CheckOrderMapper orderMapper;

    public IPage<CheckOrder> page(int current, int size, String residentName, String idCard,
                                   Long deptId, Integer checkYear, Integer status) {
        Page<CheckOrder> pageParam = new Page<>(current, size);
        return orderMapper.selectOrderPage(pageParam, residentName, idCard, deptId, checkYear, status);
    }

    public CheckOrder getById(Long id) {
        return orderMapper.selectById(id);
    }

    public CheckOrder getByOrderNo(String orderNo) {
        return orderMapper.selectOne(
                new LambdaQueryWrapper<CheckOrder>().eq(CheckOrder::getOrderNo, orderNo).eq(CheckOrder::getDeleted, 0)
        );
    }

    public void create(CheckOrder order) {
        if (order.getOrderNo() == null || order.getOrderNo().isEmpty()) {
            order.setOrderNo(generateOrderNo());
        }
        if (order.getStatus() == null) order.setStatus(0);
        if (order.getCheckYear() == null) order.setCheckYear(LocalDate.now().getYear());
        if (order.getCheckDate() == null) order.setCheckDate(LocalDate.now());
        orderMapper.insert(order);
    }

    public void update(CheckOrder order) {
        orderMapper.updateById(order);
    }

    public void updateStatus(Long id, Integer status) {
        CheckOrder order = new CheckOrder();
        order.setId(id);
        order.setStatus(status);
        orderMapper.updateById(order);
    }

    public long countByYear(Integer year) {
        if (year == null) year = LocalDate.now().getYear();
        return orderMapper.selectCount(
                new LambdaQueryWrapper<CheckOrder>()
                        .eq(CheckOrder::getCheckYear, year)
                        .eq(CheckOrder::getDeleted, 0)
        );
    }

    public void delete(Long id) {
        CheckOrder order = new CheckOrder();
        order.setId(id);
        order.setDeleted(1);
        orderMapper.updateById(order);
    }

    private String generateOrderNo() {
        String date = LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        return "CK" + date + String.format("%04d", (int)(Math.random() * 9999 + 1));
    }
}
