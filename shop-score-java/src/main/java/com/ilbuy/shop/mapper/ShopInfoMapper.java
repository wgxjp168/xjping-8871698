package com.ilbuy.shop.mapper;

import com.ilbuy.shop.dto.ShopInfoQueryDTO;
import com.ilbuy.shop.entity.ShopInfo;
import com.ilbuy.shop.vo.ShopInfoVO;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface ShopInfoMapper {

    int insert(ShopInfo shopInfo);

    int updateById(ShopInfo shopInfo);

    /** 逻辑删除（状态设为关闭） */
    int deleteById(@Param("shopId") Long shopId);

    ShopInfo selectById(@Param("shopId") Long shopId);

    /** 分页列表（JOIN类目表取名称） */
    List<ShopInfoVO> selectPage(ShopInfoQueryDTO query);

    /** 导出用全量查询 */
    List<ShopInfoVO> selectForExport(ShopInfoQueryDTO query);
}
