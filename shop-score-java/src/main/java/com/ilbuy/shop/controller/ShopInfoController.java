package com.ilbuy.shop.controller;

import com.ilbuy.shop.common.ExcelUtil;
import com.ilbuy.shop.common.PageResult;
import com.ilbuy.shop.common.Result;
import com.ilbuy.shop.dto.ShopInfoDTO;
import com.ilbuy.shop.dto.ShopInfoQueryDTO;
import com.ilbuy.shop.entity.ShopInfo;
import com.ilbuy.shop.service.ShopInfoService;
import com.ilbuy.shop.vo.ShopInfoVO;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * 商铺管理
 */
@RestController
@RequestMapping("/shop/info")
@RequiredArgsConstructor
public class ShopInfoController {

    private final ShopInfoService shopInfoService;

    /** 新增商铺 */
    @PostMapping("/add")
    public Result<Long> add(@Validated @RequestBody ShopInfoDTO dto) {
        return Result.ok(shopInfoService.add(dto));
    }

    /** 修改商铺 */
    @PostMapping("/update")
    public Result<Void> update(@Validated @RequestBody ShopInfoDTO dto) {
        shopInfoService.update(dto);
        return Result.ok();
    }

    /** 删除商铺（逻辑删除） */
    @PostMapping("/delete/{shopId}")
    public Result<Void> delete(@PathVariable Long shopId) {
        shopInfoService.delete(shopId);
        return Result.ok();
    }

    /** 商铺详情 */
    @GetMapping("/detail/{shopId}")
    public Result<ShopInfo> detail(@PathVariable Long shopId) {
        return Result.ok(shopInfoService.getById(shopId));
    }

    /** 分页列表 */
    @GetMapping("/page")
    public Result<PageResult<ShopInfoVO>> page(@Validated ShopInfoQueryDTO query) {
        return Result.ok(shopInfoService.page(query));
    }

    /**
     * 导出 Excel
     * GET /shop/info/export?shopName=xx&cateId=1&shopStatus=1
     */
    @GetMapping("/export")
    public void export(ShopInfoQueryDTO query, HttpServletResponse response) throws IOException {
        ExcelUtil.export(response, "商铺列表", "商铺",
            ShopInfoVO.class, shopInfoService.listForExport(query));
    }
}
