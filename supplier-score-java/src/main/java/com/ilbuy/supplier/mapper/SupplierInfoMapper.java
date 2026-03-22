package com.ilbuy.supplier.mapper;

import com.ilbuy.supplier.dto.SupplierInfoQueryDTO;
import com.ilbuy.supplier.entity.SupplierInfo;
import com.ilbuy.supplier.vo.SupplierInfoVO;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface SupplierInfoMapper {

    int insert(SupplierInfo supplierInfo);

    int updateById(SupplierInfo supplierInfo);

    /** 逻辑删除（状态设为关闭） */
    int deleteById(@Param("supplierId") Long supplierId);

    SupplierInfo selectById(@Param("supplierId") Long supplierId);

    /** 分页列表（JOIN分类表取名称） */
    List<SupplierInfoVO> selectPage(SupplierInfoQueryDTO query);

    /** 导出全量查询 */
    List<SupplierInfoVO> selectForExport(SupplierInfoQueryDTO query);
}
