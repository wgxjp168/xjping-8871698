package com.health.controller;

import com.health.common.PageResult;
import com.health.common.Result;
import com.health.dto.CheckOrderQueryDTO;
import com.health.dto.CheckResultSaveDTO;
import com.health.entity.CheckOrder;
import com.health.service.CheckService;
import com.health.vo.CheckOrderVO;
import com.health.vo.CheckResultVO;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 体检管理接口
 */
@Api(tags = "体检管理")
@RestController
@RequestMapping("/check")
@RequiredArgsConstructor
public class CheckController {

    private final CheckService checkService;

    @ApiOperation("分页查询体检单")
    @GetMapping("/order/page")
    public Result<PageResult<CheckOrderVO>> orderPage(CheckOrderQueryDTO query) {
        return Result.success(checkService.queryOrderPage(query));
    }

    @ApiOperation("获取体检单详情")
    @GetMapping("/order/{orderId}")
    public Result<CheckOrderVO> orderDetail(@PathVariable Long orderId) {
        return Result.success(checkService.getOrderDetail(orderId));
    }

    @ApiOperation("创建体检单")
    @PostMapping("/order")
    public Result<CheckOrder> createOrder(@RequestParam Long patientId,
                                          @RequestParam(required = false) Long packageId) {
        return Result.success(checkService.createOrder(patientId, packageId));
    }

    @ApiOperation("更新体检单状态")
    @PutMapping("/order/{orderId}/status")
    public Result<Void> updateStatus(@PathVariable Long orderId,
                                     @RequestParam String status) {
        checkService.updateOrderStatus(orderId, status);
        return Result.success();
    }

    @ApiOperation("保存体检结果")
    @PostMapping("/result")
    public Result<Void> saveResult(@Validated @RequestBody CheckResultSaveDTO dto) {
        checkService.saveResult(dto);
        return Result.success();
    }

    @ApiOperation("获取体检结果列表")
    @GetMapping("/result/{orderId}")
    public Result<List<CheckResultVO>> getResults(@PathVariable Long orderId) {
        return Result.success(checkService.getResultsByOrderId(orderId));
    }
}
