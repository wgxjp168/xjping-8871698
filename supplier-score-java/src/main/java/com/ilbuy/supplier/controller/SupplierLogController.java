package com.ilbuy.supplier.controller;

import com.ilbuy.supplier.common.ExcelUtil;
import com.ilbuy.supplier.common.PageResult;
import com.ilbuy.supplier.common.Result;
import com.ilbuy.supplier.dto.SupplierLogQueryDTO;
import com.ilbuy.supplier.service.SupplierLogService;
import com.ilbuy.supplier.vo.SupplierLogVO;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * 操作日志查询（只读，写入由各 Service 内部调用）
 */
@RestController
@RequestMapping("/supplier/log")
@RequiredArgsConstructor
public class SupplierLogController {

    private final SupplierLogService logService;

    /**
     * 分页查询
     * GET /supplier/log/page?supplierId=&operateType=&operateUser=&operateTimeStart=&operateTimeEnd=
     */
    @GetMapping("/page")
    public Result<PageResult<SupplierLogVO>> page(@Validated SupplierLogQueryDTO query) {
        return Result.ok(logService.page(query));
    }

    /**
     * 导出 Excel
     */
    @GetMapping("/export")
    public void export(SupplierLogQueryDTO query, HttpServletResponse response) throws IOException {
        ExcelUtil.export(response, "操作日志", "日志",
            SupplierLogVO.class, logService.listForExport(query));
    }
}
