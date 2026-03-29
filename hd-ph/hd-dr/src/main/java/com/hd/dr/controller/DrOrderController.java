package com.hd.dr.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.hd.common.result.Result;
import com.hd.dr.entity.DrOrder;
import com.hd.dr.service.DrOrderService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/dr-orders")
public class DrOrderController {

    @Autowired
    private DrOrderService orderService;

    @GetMapping
    public Result<IPage<DrOrder>> page(
            @RequestParam(defaultValue = "1") int current,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String residentName,
            @RequestParam(required = false) String idCard,
            @RequestParam(required = false) Integer status,
            @RequestParam(required = false) Long applyDeptId) {
        return Result.success(orderService.page(current, size, residentName, idCard, status, applyDeptId));
    }

    @GetMapping("/{id}")
    public Result<DrOrder> getById(@PathVariable Long id) {
        return Result.success(orderService.getById(id));
    }

    @GetMapping("/barcode/{barcodeNo}")
    public Result<DrOrder> getByBarcode(@PathVariable String barcodeNo) {
        return Result.success(orderService.getByBarcodeNo(barcodeNo));
    }

    @PostMapping
    public Result<DrOrder> create(@RequestBody DrOrder order,
                                   @RequestHeader(value = "X-User-Id", required = false) Long userId) {
        order.setApplyUserId(userId);
        orderService.create(order);
        return Result.success(order);
    }

    /**
     * DR扫码签到接口
     * POST /api/dr-orders/scan
     * { "barcodeNo": "BC20240101...", "scanUserId": 5 }
     */
    @PostMapping("/scan")
    public Result<DrOrder> scan(@RequestBody Map<String, Object> body,
                                 @RequestHeader(value = "X-User-Id", required = false) Long userId) {
        String barcodeNo = (String) body.get("barcodeNo");
        Long scanUserId = userId != null ? userId : (body.get("scanUserId") != null ?
                Long.valueOf(body.get("scanUserId").toString()) : null);
        DrOrder order = orderService.scanBarcode(barcodeNo, scanUserId);
        return Result.success(order);
    }

    @PutMapping("/{id}/status")
    public Result<Void> updateStatus(@PathVariable Long id, @RequestBody Map<String, Integer> body) {
        orderService.updateStatus(id, body.get("status"));
        return Result.success(null);
    }

    @GetMapping("/count/month")
    public Result<Long> countThisMonth() {
        return Result.success(orderService.countThisMonth());
    }

    @DeleteMapping("/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        orderService.delete(id);
        return Result.success(null);
    }

    @GetMapping("/health")
    public Result<String> health() {
        return Result.success("hd-dr OK");
    }
}
