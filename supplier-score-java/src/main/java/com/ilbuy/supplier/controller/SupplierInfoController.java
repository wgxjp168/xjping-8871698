package com.ilbuy.supplier.controller;

import com.ilbuy.supplier.common.ExcelUtil;
import com.ilbuy.supplier.common.PageResult;
import com.ilbuy.supplier.common.Result;
import com.ilbuy.supplier.dto.SupplierInfoDTO;
import com.ilbuy.supplier.dto.SupplierInfoQueryDTO;
import com.ilbuy.supplier.entity.SupplierInfo;
import com.ilbuy.supplier.service.SupplierInfoService;
import com.ilbuy.supplier.vo.SupplierInfoVO;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * 供应商管理
 */
@RestController
@RequestMapping("/supplier/info")
@RequiredArgsConstructor
public class SupplierInfoController {

    private final SupplierInfoService supplierInfoService;

    /** 新增供应商 */
    @PostMapping("/add")
    public Result<Long> add(@Validated @RequestBody SupplierInfoDTO dto) {
        return Result.ok(supplierInfoService.add(dto));
    }

    /** 修改供应商 */
    @PostMapping("/update")
    public Result<Void> update(@Validated @RequestBody SupplierInfoDTO dto) {
        supplierInfoService.update(dto);
        return Result.ok();
    }

    /** 删除供应商（逻辑删除） */
    @PostMapping("/delete/{supplierId}")
    public Result<Void> delete(@PathVariable Long supplierId) {
        supplierInfoService.delete(supplierId);
        return Result.ok();
    }

    /** 供应商详情 */
    @GetMapping("/detail/{supplierId}")
    public Result<SupplierInfo> detail(@PathVariable Long supplierId) {
        return Result.ok(supplierInfoService.getById(supplierId));
    }

    /** 分页列表 */
    @GetMapping("/page")
    public Result<PageResult<SupplierInfoVO>> page(@Validated SupplierInfoQueryDTO query) {
        return Result.ok(supplierInfoService.page(query));
    }

    /**
     * 导出 Excel
     * GET /supplier/info/export?supplierName=xx&cateId=1&supplierStatus=1
     */
    @GetMapping("/export")
    public void export(SupplierInfoQueryDTO query, HttpServletResponse response) throws IOException {
        ExcelUtil.export(response, "供应商列表", "供应商",
            SupplierInfoVO.class, supplierInfoService.listForExport(query));
    }
}
