package com.ilbuy.shop.mapper;

import com.ilbuy.shop.dto.ShopViolationQueryDTO;
import com.ilbuy.shop.entity.ShopViolation;
import com.ilbuy.shop.vo.ShopViolationVO;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface ShopViolationMapper {

    int insert(ShopViolation vio);

    int updateById(ShopViolation vio);

    int deleteById(@Param("id") Long id);

    ShopViolation selectById(@Param("id") Long id);

    /** 分页列表（JOIN shop_info） */
    List<ShopViolationVO> selectPage(ShopViolationQueryDTO query);

    /** 导出全量 */
    List<ShopViolationVO> selectForExport(ShopViolationQueryDTO query);
}
