package com.ilbuy.supplier.mapper;

import com.ilbuy.supplier.entity.SupplierCategory;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface SupplierCategoryMapper {

    int insert(SupplierCategory category);

    int updateById(SupplierCategory category);

    int deleteById(@Param("id") Integer id);

    SupplierCategory selectById(@Param("id") Integer id);

    /** 查询所有（可按 status 过滤，null 则查全部） */
    List<SupplierCategory> selectList(@Param("status") Integer status);
}
