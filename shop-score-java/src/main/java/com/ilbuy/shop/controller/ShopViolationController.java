package com.ilbuy.shop.controller;

import com.ilbuy.shop.common.ExcelUtil;
import com.ilbuy.shop.common.PageResult;
import com.ilbuy.shop.common.Result;
import com.ilbuy.shop.dto.ShopViolationDTO;
import com.ilbuy.shop.dto.ShopViolationQueryDTO;
import com.ilbuy.shop.entity.ShopViolation;
import com.ilbuy.shop.service.ShopViolationService;
import com.ilbuy.shop.vo.ShopViolationVO;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

/**
 * 违规记录管理
 */
@RestController
@RequestMapping("/shop/violation")
@RequiredArgsConstructor
public class ShopViolationController {

    private final ShopViolationService violationService;

    /** 新增违规记录 */
    @PostMapping("/add")
    public Result<Long> add(@Validated @RequestBody ShopViolationDTO dto) {
        return Result.ok(violationService.add(dto));
    }

    /** 修改违规记录 */
    @PostMapping("/update/{id}")
    public Result<Void> update(@PathVariable Long id,
                               @Validated @RequestBody ShopViolationDTO dto) {
        violationService.update(id, dto);
        return Result.ok();
    }

    /** 删除违规记录 */
    @PostMapping("/delete/{id}")
    public Result<Void> delete(@PathVariable Long id) {
        violationService.delete(id);
        return Result.ok();
    }

    /** 详情 */
    @GetMapping("/detail/{id}")
    public Result<ShopViolation> detail(@PathVariable Long id) {
        return Result.ok(violationService.getById(id));
    }

    /**
     * 分页列表
     * GET /shop/violation/page?shopId=&vioType=&vioTimeStart=&vioTimeEnd=
     */
    @GetMapping("/page")
    public Result<PageResult<ShopViolationVO>> page(@Validated ShopViolationQueryDTO query) {
        return Result.ok(violationService.page(query));
    }

    /**
     * 导出 Excel
     */
    @GetMapping("/export")
    public void export(ShopViolationQueryDTO query, HttpServletResponse response) throws IOException {
        ExcelUtil.export(response, "违规记录", "违规",
            ShopViolationVO.class, violationService.listForExport(query));
    }
}
