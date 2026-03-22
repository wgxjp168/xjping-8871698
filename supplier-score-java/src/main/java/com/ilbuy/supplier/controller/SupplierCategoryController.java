package com.ilbuy.supplier.controller;

import com.ilbuy.supplier.common.Result;
import com.ilbuy.supplier.dto.SupplierCategoryDTO;
import com.ilbuy.supplier.entity.SupplierCategory;
import com.ilbuy.supplier.service.SupplierCategoryService;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * 供应商分类管理
 */
@RestController
@RequestMapping("/supplier/category")
@RequiredArgsConstructor
public class SupplierCategoryController {

    private final SupplierCategoryService categoryService;

    /** 新增分类 */
    @PostMapping("/add")
    public Result<Integer> add(@Validated @RequestBody SupplierCategoryDTO dto) {
        return Result.ok(categoryService.add(dto));
    }

    /** 修改分类 */
    @PostMapping("/update")
    public Result<Void> update(@Validated @RequestBody SupplierCategoryDTO dto) {
        categoryService.update(dto);
        return Result.ok();
    }

    /** 删除分类 */
    @PostMapping("/delete/{id}")
    public Result<Void> delete(@PathVariable Integer id) {
        categoryService.delete(id);
        return Result.ok();
    }

    /** 详情 */
    @GetMapping("/detail/{id}")
    public Result<SupplierCategory> detail(@PathVariable Integer id) {
        return Result.ok(categoryService.getById(id));
    }

    /**
     * 列表
     * @param status 1=启用，0=禁用，不传=全部
     */
    @GetMapping("/list")
    public Result<List<SupplierCategory>> list(@RequestParam(required = false) Integer status) {
        return Result.ok(categoryService.list(status));
    }
}
