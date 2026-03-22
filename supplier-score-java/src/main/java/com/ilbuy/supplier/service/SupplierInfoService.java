package com.ilbuy.supplier.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.ilbuy.supplier.common.PageResult;
import com.ilbuy.supplier.dto.SupplierInfoDTO;
import com.ilbuy.supplier.dto.SupplierInfoQueryDTO;
import com.ilbuy.supplier.entity.SupplierInfo;
import com.ilbuy.supplier.mapper.SupplierInfoMapper;
import com.ilbuy.supplier.mapper.SupplierLogMapper;
import com.ilbuy.supplier.vo.SupplierInfoVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.Assert;

import java.util.List;

@Service
@RequiredArgsConstructor
public class SupplierInfoService {

    private final SupplierInfoMapper supplierInfoMapper;
    private final SupplierLogMapper  logMapper;

    /** 新增供应商 */
    @Transactional(rollbackFor = Exception.class)
    public Long add(SupplierInfoDTO dto) {
        SupplierInfo entity = toEntity(dto);
        entity.setSupplierStatus(1); // 默认正常
        supplierInfoMapper.insert(entity);
        addLog(entity.getSupplierId(), "新增供应商", "供应商名称：" + entity.getSupplierName(), "system");
        return entity.getSupplierId();
    }

    /** 修改供应商 */
    @Transactional(rollbackFor = Exception.class)
    public void update(SupplierInfoDTO dto) {
        Assert.notNull(dto.getSupplierId(), "供应商ID不能为空");
        SupplierInfo entity = toEntity(dto);
        supplierInfoMapper.updateById(entity);
        addLog(dto.getSupplierId(), "修改供应商", "供应商ID：" + dto.getSupplierId(), "system");
    }

    /** 删除供应商（逻辑删除） */
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long supplierId) {
        supplierInfoMapper.deleteById(supplierId);
        addLog(supplierId, "删除供应商", "供应商ID：" + supplierId, "system");
    }

    /** 详情 */
    public SupplierInfo getById(Long supplierId) {
        SupplierInfo info = supplierInfoMapper.selectById(supplierId);
        Assert.notNull(info, "供应商不存在");
        return info;
    }

    /** 分页列表 */
    public PageResult<SupplierInfoVO> page(SupplierInfoQueryDTO query) {
        PageHelper.startPage(query.getPageNum(), query.getPageSize());
        List<SupplierInfoVO> list = supplierInfoMapper.selectPage(query);
        return PageResult.of(new PageInfo<>(list));
    }

    /** 导出数据（不分页） */
    public List<SupplierInfoVO> listForExport(SupplierInfoQueryDTO query) {
        return supplierInfoMapper.selectForExport(query);
    }

    // -------- private --------

    private SupplierInfo toEntity(SupplierInfoDTO dto) {
        SupplierInfo entity = new SupplierInfo();
        entity.setSupplierId(dto.getSupplierId());
        entity.setSupplierName(dto.getSupplierName());
        entity.setCateId(dto.getCateId());
        entity.setCreditCode(dto.getCreditCode());
        entity.setContactUser(dto.getContactUser());
        entity.setContactPhone(dto.getContactPhone());
        entity.setAddress(dto.getAddress());
        entity.setQualification(dto.getQualification());
        entity.setSupplierStatus(dto.getSupplierStatus());
        return entity;
    }

    private void addLog(Long supplierId, String type, String content, String user) {
        com.ilbuy.supplier.entity.SupplierLog log = new com.ilbuy.supplier.entity.SupplierLog();
        log.setSupplierId(supplierId);
        log.setOperateType(type);
        log.setOperateContent(content);
        log.setOperateUser(user);
        logMapper.insert(log);
    }
}
