package com.ilbuy.shop.controller;

import com.ilbuy.shop.common.ExcelUtil;
import com.ilbuy.shop.common.PageResult;
import com.ilbuy.shop.common.Result;
import com.ilbuy.shop.dto.ShopScoreDTO;
import com.ilbuy.shop.dto.ShopScoreQueryDTO;
import com.ilbuy.shop.service.ShopScoreService;
import com.ilbuy.shop.vo.ShopScoreDetailVO;
import com.ilbuy.shop.vo.ShopScoreMainVO;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * 商铺评分管理
 */
@RestController
@RequestMapping("/shop/score")
@RequiredArgsConstructor
public class ShopScoreController {

    private final ShopScoreService shopScoreService;

    /**
     * 提交评分
     * POST /shop/score/save
     * Body: ShopScoreDTO（shopId / scorePeriod / scoreUser / opinion / itemList）
     * 返回: mainId
     */
    @PostMapping("/save")
    public Result<Long> save(@Validated @RequestBody ShopScoreDTO dto) {
        return Result.ok(shopScoreService.saveScore(dto));
    }

    /**
     * 评分详情（含各维度明细）
     * GET /shop/score/detail/{mainId}
     */
    @GetMapping("/detail/{mainId}")
    public Result<ShopScoreDetailVO> detail(@PathVariable Long mainId) {
        return Result.ok(shopScoreService.getDetail(mainId));
    }

    /**
     * 分页列表
     * GET /shop/score/page?pageNum=1&pageSize=20&shopId=&scorePeriod=&shopLevel=
     */
    @GetMapping("/page")
    public Result<PageResult<ShopScoreMainVO>> page(@Validated ShopScoreQueryDTO query) {
        return Result.ok(shopScoreService.page(query));
    }

    /**
     * 导出 Excel
     * GET /shop/score/export?shopId=&scorePeriod=&shopLevel=
     */
    @GetMapping("/export")
    public void export(ShopScoreQueryDTO query, HttpServletResponse response) throws IOException {
        ExcelUtil.export(response, "评分列表", "评分",
            ShopScoreMainVO.class, shopScoreService.listForExport(query));
    }
}
