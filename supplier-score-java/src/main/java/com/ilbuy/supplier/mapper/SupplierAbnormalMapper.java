package com.ilbuy.supplier.mapper;

import com.ilbuy.supplier.dto.SupplierAbnormalQueryDTO;
import com.ilbuy.supplier.entity.SupplierAbnormal;
import com.ilbuy.supplier.vo.SupplierAbnormalVO;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface SupplierAbnormalMapper {

    int insert(SupplierAbnormal abnormal);

    int updateById(SupplierAbnormal abnormal);

    int deleteById(@Param("id") Long id);

    SupplierAbnormal selectById(@Param("id") Long id);

    /** 分页列表（JOIN supplier_info） */
    List<SupplierAbnormalVO> selectPage(SupplierAbnormalQueryDTO query);

    /** 导出全量 */
    List<SupplierAbnormalVO> selectForExport(SupplierAbnormalQueryDTO query);
}
