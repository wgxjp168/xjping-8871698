package com.ilbuy.shop.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.ilbuy.shop.common.PageResult;
import com.ilbuy.shop.dto.ShopLogQueryDTO;
import com.ilbuy.shop.mapper.ShopLogMapper;
import com.ilbuy.shop.vo.ShopOperateLogVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ShopOperateLogService {

    private final ShopLogMapper logMapper;

    /** 分页查询操作日志 */
    public PageResult<ShopOperateLogVO> page(ShopLogQueryDTO query) {
        PageHelper.startPage(query.getPageNum(), query.getPageSize());
        List<ShopOperateLogVO> list = logMapper.selectPage(query);
        return PageResult.of(new PageInfo<>(list));
    }

    /** 导出操作日志 */
    public List<ShopOperateLogVO> listForExport(ShopLogQueryDTO query) {
        return logMapper.selectForExport(query);
    }
}
