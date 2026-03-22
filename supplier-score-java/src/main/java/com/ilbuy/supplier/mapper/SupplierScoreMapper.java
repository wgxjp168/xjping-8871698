package com.ilbuy.supplier.mapper;

import com.ilbuy.supplier.dto.SupplierScoreQueryDTO;
import com.ilbuy.supplier.entity.SupplierScoreItem;
import com.ilbuy.supplier.entity.SupplierScoreMain;
import com.ilbuy.supplier.vo.SupplierScoreDetailVO;
import com.ilbuy.supplier.vo.SupplierScoreMainVO;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface SupplierScoreMapper {

    int insertMain(SupplierScoreMain main);

    int batchInsertItem(@Param("list") List<SupplierScoreItem> list);

    SupplierScoreMain selectBySupplierAndPeriod(@Param("supplierId") Long supplierId,
                                                @Param("period") String period);

    SupplierScoreMain selectMainById(@Param("mainId") Long mainId);

    /** 评分明细列表（含类型名） */
    List<SupplierScoreDetailVO.ItemVO> selectItemsByMainId(@Param("mainId") Long mainId);

    /** 分页列表（JOIN supplier_info 取供应商名） */
    List<SupplierScoreMainVO> selectPage(SupplierScoreQueryDTO query);

    /** 导出全量 */
    List<SupplierScoreMainVO> selectForExport(SupplierScoreQueryDTO query);
}
