package com.ilbuy.supplier.controller;

import com.ilbuy.supplier.common.ExcelUtil;
import com.ilbuy.supplier.common.PageResult;
import com.ilbuy.supplier.common.Result;
import com.ilbuy.supplier.dto.SupplierScoreDTO;
import com.ilbuy.supplier.dto.SupplierScoreQueryDTO;
import com.ilbuy.supplier.service.SupplierScoreService;
import com.ilbuy.supplier.vo.SupplierScoreDetailVO;
import com.ilbuy.supplier.vo.SupplierScoreMainVO;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * 供应商评分管理
 */
@RestController
@RequestMapping("/supplier/score")
@RequiredArgsConstructor
public class SupplierScoreController {

    private final SupplierScoreService supplierScoreService;

    /**
     * 提交评分
     * POST /supplier/score/save
     * Body: SupplierScoreDTO（supplierId / scorePeriod / scoreUser / opinion / itemList）
     * 返回: mainId
     */
    @PostMapping("/save")
    public Result<Long> save(@Validated @RequestBody SupplierScoreDTO dto) {
        return Result.ok(supplierScoreService.saveScore(dto));
    }

    /**
     * 评分详情（含各维度明细）
     * GET /supplier/score/detail/{mainId}
     */
    @GetMapping("/detail/{mainId}")
    public Result<SupplierScoreDetailVO> detail(@PathVariable Long mainId) {
        return Result.ok(supplierScoreService.getDetail(mainId));
    }

    /**
     * 分页列表
     * GET /supplier/score/page?pageNum=1&pageSize=20&supplierId=&scorePeriod=&supplierLevel=
     */
    @GetMapping("/page")
    public Result<PageResult<SupplierScoreMainVO>> page(@Validated SupplierScoreQueryDTO query) {
        return Result.ok(supplierScoreService.page(query));
    }

    /**
     * 导出 Excel
     * GET /supplier/score/export?supplierId=&scorePeriod=&supplierLevel=
     */
    @GetMapping("/export")
    public void export(SupplierScoreQueryDTO query, HttpServletResponse response) throws IOException {
        ExcelUtil.export(response, "评分列表", "评分",
            SupplierScoreMainVO.class, supplierScoreService.listForExport(query));
    }
}
