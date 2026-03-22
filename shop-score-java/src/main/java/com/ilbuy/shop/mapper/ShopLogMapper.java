package com.ilbuy.shop.mapper;

import com.ilbuy.shop.dto.ShopLogQueryDTO;
import com.ilbuy.shop.entity.ShopOperateLog;
import com.ilbuy.shop.vo.ShopOperateLogVO;

import java.util.List;

public interface ShopLogMapper {

    int insert(ShopOperateLog log);

    /** 分页列表（JOIN shop_info） */
    List<ShopOperateLogVO> selectPage(ShopLogQueryDTO query);

    /** 导出全量 */
    List<ShopOperateLogVO> selectForExport(ShopLogQueryDTO query);
}
