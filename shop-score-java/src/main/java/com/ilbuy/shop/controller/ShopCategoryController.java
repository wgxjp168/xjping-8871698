package com.ilbuy.shop.controller;

import com.ilbuy.shop.common.Result;
import com.ilbuy.shop.dto.ShopCategoryDTO;
import com.ilbuy.shop.entity.ShopCategory;
import com.ilbuy.shop.service.ShopCategoryService;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 商铺类目管理
 */
@RestController
@RequestMapping("/shop/category")
@RequiredArgsConstructor
public class ShopCategoryController {

    private final ShopCategoryService categoryService;

    /** 新增类目 */
    @PostMapping("/add")
    public Result<Integer> add(@Validated @RequestBody ShopCategoryDTO dto) {
        return Result.ok(categoryService.add(dto));
    }

    /** 修改类目 */
    @PostMapping("/update")
    public Result<Void> update(@Validated @RequestBody ShopCategoryDTO dto) {
        categoryService.update(dto);
        return Result.ok();
    }

    /** 删除类目 */
    @PostMapping("/delete/{id}")
    public Result<Void> delete(@PathVariable Integer id) {
        categoryService.delete(id);
        return Result.ok();
    }

    /** 详情 */
    @GetMapping("/detail/{id}")
    public Result<ShopCategory> detail(@PathVariable Integer id) {
        return Result.ok(categoryService.getById(id));
    }

    /**
     * 列表
     * @param status 1=启用，0=禁用，不传=全部
     */
    @GetMapping("/list")
    public Result<List<ShopCategory>> list(@RequestParam(required = false) Integer status) {
        return Result.ok(categoryService.list(status));
    }
}
