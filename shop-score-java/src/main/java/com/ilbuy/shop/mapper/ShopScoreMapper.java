package com.ilbuy.shop.mapper;

import com.ilbuy.shop.dto.ShopScoreQueryDTO;
import com.ilbuy.shop.entity.ShopScoreItem;
import com.ilbuy.shop.entity.ShopScoreMain;
import com.ilbuy.shop.vo.ShopScoreDetailVO;
import com.ilbuy.shop.vo.ShopScoreMainVO;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface ShopScoreMapper {

    int insertMain(ShopScoreMain main);

    int batchInsertItem(@Param("list") List<ShopScoreItem> list);

    ShopScoreMain selectByShopAndPeriod(@Param("shopId") Long shopId,
                                        @Param("period") String period);

    ShopScoreMain selectMainById(@Param("mainId") Long mainId);

    /** 评分明细列表（含规则名） */
    List<ShopScoreDetailVO.ItemVO> selectItemsByMainId(@Param("mainId") Long mainId);

    /** 分页列表（JOIN shop_info 取商铺名） */
    List<ShopScoreMainVO> selectPage(ShopScoreQueryDTO query);

    /** 导出全量 */
    List<ShopScoreMainVO> selectForExport(ShopScoreQueryDTO query);
}
