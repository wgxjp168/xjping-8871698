package com.ilbuy.shop.service;

import com.ilbuy.shop.dto.ShopCategoryDTO;
import com.ilbuy.shop.entity.ShopCategory;
import com.ilbuy.shop.mapper.ShopCategoryMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.util.Assert;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ShopCategoryService {

    private final ShopCategoryMapper categoryMapper;

    /** 新增类目 */
    public Integer add(ShopCategoryDTO dto) {
        ShopCategory entity = new ShopCategory();
        entity.setCateName(dto.getCateName());
        entity.setSort(dto.getSort() != null ? dto.getSort() : 0);
        entity.setStatus(dto.getStatus() != null ? dto.getStatus() : 1);
        categoryMapper.insert(entity);
        return entity.getId();
    }

    /** 修改类目 */
    public void update(ShopCategoryDTO dto) {
        Assert.notNull(dto.getId(), "类目ID不能为空");
        ShopCategory entity = new ShopCategory();
        entity.setId(dto.getId());
        entity.setCateName(dto.getCateName());
        entity.setSort(dto.getSort());
        entity.setStatus(dto.getStatus());
        categoryMapper.updateById(entity);
    }

    /** 删除类目 */
    public void delete(Integer id) {
        categoryMapper.deleteById(id);
    }

    /** 详情 */
    public ShopCategory getById(Integer id) {
        ShopCategory cate = categoryMapper.selectById(id);
        Assert.notNull(cate, "类目不存在");
        return cate;
    }

    /** 列表（status=null 查全部，status=1 只查启用） */
    public List<ShopCategory> list(Integer status) {
        return categoryMapper.selectList(status);
    }
}
