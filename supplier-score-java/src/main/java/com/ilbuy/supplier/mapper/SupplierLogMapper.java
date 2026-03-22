package com.ilbuy.supplier.mapper;

import com.ilbuy.supplier.dto.SupplierLogQueryDTO;
import com.ilbuy.supplier.entity.SupplierLog;
import com.ilbuy.supplier.vo.SupplierLogVO;

import java.util.List;

public interface SupplierLogMapper {

    int insert(SupplierLog log);

    /** 分页列表（JOIN supplier_info） */
    List<SupplierLogVO> selectPage(SupplierLogQueryDTO query);

    /** 导出全量 */
    List<SupplierLogVO> selectForExport(SupplierLogQueryDTO query);
}
