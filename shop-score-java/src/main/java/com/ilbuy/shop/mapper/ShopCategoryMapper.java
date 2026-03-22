package com.ilbuy.shop.mapper;

import com.ilbuy.shop.entity.ShopCategory;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface ShopCategoryMapper {

    int insert(ShopCategory category);

    int updateById(ShopCategory category);

    int deleteById(@Param("id") Integer id);

    ShopCategory selectById(@Param("id") Integer id);

    /** 查询所有（可按 status 过滤，null 则查全部） */
    List<ShopCategory> selectList(@Param("status") Integer status);
}
