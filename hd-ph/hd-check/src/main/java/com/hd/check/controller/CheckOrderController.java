package com.hd.check.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.hd.check.entity.CheckOrder;
import com.hd.check.service.CheckOrderService;
import com.hd.common.result.Result;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/check-orders")
public class CheckOrderController {

    @Autowired
    private CheckOrderService orderService;

    @GetMapping
    public Result<IPage<CheckOrder>> page(
            @RequestParam(defaultValue = "1") int current,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String residentName,
            @RequestParam(required = false) String idCard,
            @RequestParam(required = false) Long deptId,
            @RequestParam(required = false) Integer checkYear,
            @RequestParam(required = false) Integer status) {
        return Result.success(orderService.page(current, size, residentName, idCard, deptId, checkYear, status));
    }

    @GetMapping("/{id}")
    public Result<CheckOrder> getById(@PathVariable Long id) {
        return Result.success(orderService.getById(id));
    }

    @GetMapping("/by-no/{orderNo}")
    public Result<CheckOrder> getByOrderNo(@PathVariable String orderNo) {
        return Result.success(orderService.getByOrderNo(orderNo));
    }

    @PostMapping
    public Result<CheckOrder> create(@RequestBody CheckOrder order) {
        orderService.create(order);
        return Result.success(order);
    }

    @PutMapping("/{id}")
    public Result<Void> update(@PathVariable Long id, @RequestBody CheckOrder order) {
        order.setId(id);
        orderService.update(order);
        return Result.success(null);
    }

    @PutMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestBody Map<String, Integer> body) {
        orderService.updateStatus(id, body.get("status"));
        return Result.success(null);
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        orderService.delete(id);
        return Result.success(null);
    }
}
