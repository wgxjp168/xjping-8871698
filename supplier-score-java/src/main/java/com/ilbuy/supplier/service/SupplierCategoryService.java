package com.ilbuy.supplier.service;

import com.ilbuy.supplier.dto.SupplierCategoryDTO;
import com.ilbuy.supplier.entity.SupplierCategory;
import com.ilbuy.supplier.mapper.SupplierCategoryMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.util.Assert;

import java.util.List;

@Service
@RequiredArgsConstructor
public class SupplierCategoryService {

    private final SupplierCategoryMapper categoryMapper;

    /** 新增分类 */
    public Integer add(SupplierCategoryDTO dto) {
        SupplierCategory entity = new SupplierCategory();
        entity.setCateName(dto.getCateName());
        entity.setSort(dto.getSort() != null ? dto.getSort() : 0);
        entity.setStatus(dto.getStatus() != null ? dto.getStatus() : 1);
        categoryMapper.insert(entity);
        return entity.getId();
    }

    /** 修改分类 */
    public void update(SupplierCategoryDTO dto) {
        Assert.notNull(dto.getId(), "分类ID不能为空");
        SupplierCategory entity = new SupplierCategory();
        entity.setId(dto.getId());
        entity.setCateName(dto.getCateName());
        entity.setSort(dto.getSort());
        entity.setStatus(dto.getStatus());
        categoryMapper.updateById(entity);
    }

    /** 删除分类 */
    public void delete(Integer id) {
        categoryMapper.deleteById(id);
    }

    /** 详情 */
    public SupplierCategory getById(Integer id) {
        SupplierCategory cate = categoryMapper.selectById(id);
        Assert.notNull(cate, "分类不存在");
        return cate;
    }

    /** 列表（status=null 查全部，status=1 只查启用） */
    public List<SupplierCategory> list(Integer status) {
        return categoryMapper.selectList(status);
    }
}
