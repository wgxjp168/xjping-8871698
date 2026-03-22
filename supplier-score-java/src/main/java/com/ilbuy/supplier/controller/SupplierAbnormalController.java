package com.ilbuy.supplier.controller;

import com.ilbuy.supplier.common.ExcelUtil;
import com.ilbuy.supplier.common.PageResult;
import com.ilbuy.supplier.common.Result;
import com.ilbuy.supplier.dto.SupplierAbnormalDTO;
import com.ilbuy.supplier.dto.SupplierAbnormalQueryDTO;
import com.ilbuy.supplier.entity.SupplierAbnormal;
import com.ilbuy.supplier.service.SupplierAbnormalService;
import com.ilbuy.supplier.vo.SupplierAbnormalVO;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * 供应商异常记录管理
 */
@RestController
@RequestMapping("/supplier/abnormal")
@RequiredArgsConstructor
public class SupplierAbnormalController {

    private final SupplierAbnormalService abnormalService;

    /** 新增异常记录 */
    @PostMapping("/add")
    public Result<Long> add(@Validated @RequestBody SupplierAbnormalDTO dto) {
        return Result.ok(abnormalService.add(dto));
    }

    /** 修改异常记录 */
    @PostMapping("/update/{id}")
    public Result<Void> update(@PathVariable Long id,
                               @Validated @RequestBody SupplierAbnormalDTO dto) {
        abnormalService.update(id, dto);
        return Result.ok();
    }

    /** 删除异常记录 */
    @PostMapping("/delete/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        abnormalService.delete(id);
        return Result.ok();
    }

    /** 详情 */
    @GetMapping("/detail/{id}")
    public Result<SupplierAbnormal> detail(@PathVariable Long id) {
        return Result.ok(abnormalService.getById(id));
    }

    /**
     * 分页列表
     * GET /supplier/abnormal/page?supplierId=&abnType=&abnTimeStart=&abnTimeEnd=
     */
    @GetMapping("/page")
    public Result<PageResult<SupplierAbnormalVO>> page(@Validated SupplierAbnormalQueryDTO query) {
        return Result.ok(abnormalService.page(query));
    }

    /**
     * 导出 Excel
     */
    @GetMapping("/export")
    public void export(SupplierAbnormalQueryDTO query, HttpServletResponse response) throws IOException {
        ExcelUtil.export(response, "异常记录", "异常",
            SupplierAbnormalVO.class, abnormalService.listForExport(query));
    }
}
