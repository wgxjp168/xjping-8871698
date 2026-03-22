package com.ilbuy.supplier.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.ilbuy.supplier.common.PageResult;
import com.ilbuy.supplier.dto.SupplierLogQueryDTO;
import com.ilbuy.supplier.mapper.SupplierLogMapper;
import com.ilbuy.supplier.vo.SupplierLogVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class SupplierLogService {

    private final SupplierLogMapper logMapper;

    /** 分页查询操作日志 */
    public PageResult<SupplierLogVO> page(SupplierLogQueryDTO query) {
        PageHelper.startPage(query.getPageNum(), query.getPageSize());
        List<SupplierLogVO> list = logMapper.selectPage(query);
        return PageResult.of(new PageInfo<>(list));
    }

    /** 导出操作日志 */
    public List<SupplierLogVO> listForExport(SupplierLogQueryDTO query) {
        return logMapper.selectForExport(query);
    }
}
