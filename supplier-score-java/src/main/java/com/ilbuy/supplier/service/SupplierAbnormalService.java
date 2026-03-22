package com.ilbuy.supplier.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.ilbuy.supplier.common.PageResult;
import com.ilbuy.supplier.dto.SupplierAbnormalDTO;
import com.ilbuy.supplier.dto.SupplierAbnormalQueryDTO;
import com.ilbuy.supplier.entity.SupplierAbnormal;
import com.ilbuy.supplier.entity.SupplierLog;
import com.ilbuy.supplier.mapper.SupplierAbnormalMapper;
import com.ilbuy.supplier.mapper.SupplierLogMapper;
import com.ilbuy.supplier.vo.SupplierAbnormalVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.Assert;

import java.util.List;

@Service
@RequiredArgsConstructor
public class SupplierAbnormalService {

    private final SupplierAbnormalMapper abnormalMapper;
    private final SupplierLogMapper      logMapper;

    /** 新增异常记录 */
    @Transactional(rollbackFor = Exception.class)
    public Long add(SupplierAbnormalDTO dto) {
        SupplierAbnormal entity = toEntity(dto);
        abnormalMapper.insert(entity);
        addLog(dto.getSupplierId(), "新增异常",
            "异常类型：" + dto.getAbnType() + "，扣分：" + dto.getDeductionScore(), "system");
        return entity.getId();
    }

    /** 修改异常记录 */
    @Transactional(rollbackFor = Exception.class)
    public void update(Long id, SupplierAbnormalDTO dto) {
        SupplierAbnormal exist = abnormalMapper.selectById(id);
        Assert.notNull(exist, "异常记录不存在");
        SupplierAbnormal entity = toEntity(dto);
        entity.setId(id);
        abnormalMapper.updateById(entity);
        addLog(dto.getSupplierId(), "修改异常", "异常ID：" + id, "system");
    }

    /** 删除异常记录 */
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        SupplierAbnormal exist = abnormalMapper.selectById(id);
        Assert.notNull(exist, "异常记录不存在");
        abnormalMapper.deleteById(id);
        addLog(exist.getSupplierId(), "删除异常", "异常ID：" + id, "system");
    }

    /** 详情 */
    public SupplierAbnormal getById(Long id) {
        SupplierAbnormal abn = abnormalMapper.selectById(id);
        Assert.notNull(abn, "异常记录不存在");
        return abn;
    }

    /** 分页列表 */
    public PageResult<SupplierAbnormalVO> page(SupplierAbnormalQueryDTO query) {
        PageHelper.startPage(query.getPageNum(), query.getPageSize());
        List<SupplierAbnormalVO> list = abnormalMapper.selectPage(query);
        return PageResult.of(new PageInfo<>(list));
    }

    /** 导出数据 */
    public List<SupplierAbnormalVO> listForExport(SupplierAbnormalQueryDTO query) {
        return abnormalMapper.selectForExport(query);
    }

    // -------- private --------

    private SupplierAbnormal toEntity(SupplierAbnormalDTO dto) {
        SupplierAbnormal entity = new SupplierAbnormal();
        entity.setSupplierId(dto.getSupplierId());
        entity.setAbnType(dto.getAbnType());
        entity.setAbnContent(dto.getAbnContent());
        entity.setAbnTime(dto.getAbnTime());
        entity.setDeductionScore(dto.getDeductionScore());
        entity.setHandleResult(dto.getHandleResult());
        return entity;
    }

    private void addLog(Long supplierId, String type, String content, String user) {
        SupplierLog log = new SupplierLog();
        log.setSupplierId(supplierId);
        log.setOperateType(type);
        log.setOperateContent(content);
        log.setOperateUser(user);
        logMapper.insert(log);
    }
}
