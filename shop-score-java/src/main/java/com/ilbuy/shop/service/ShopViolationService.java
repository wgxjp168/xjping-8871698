package com.ilbuy.shop.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.ilbuy.shop.common.PageResult;
import com.ilbuy.shop.dto.ShopViolationDTO;
import com.ilbuy.shop.dto.ShopViolationQueryDTO;
import com.ilbuy.shop.entity.ShopOperateLog;
import com.ilbuy.shop.entity.ShopViolation;
import com.ilbuy.shop.mapper.ShopLogMapper;
import com.ilbuy.shop.mapper.ShopViolationMapper;
import com.ilbuy.shop.vo.ShopViolationVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.Assert;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ShopViolationService {

    private final ShopViolationMapper violationMapper;
    private final ShopLogMapper       logMapper;

    /** 新增违规记录 */
    @Transactional(rollbackFor = Exception.class)
    public Long add(ShopViolationDTO dto) {
        ShopViolation entity = toEntity(dto);
        violationMapper.insert(entity);
        addLog(dto.getShopId(), "新增违规",
            "违规类型：" + dto.getVioType() + "，扣分：" + dto.getDeductionScore(), "system");
        return entity.getId();
    }

    /** 修改违规记录 */
    @Transactional(rollbackFor = Exception.class)
    public void update(Long id, ShopViolationDTO dto) {
        ShopViolation exist = violationMapper.selectById(id);
        Assert.notNull(exist, "违规记录不存在");
        ShopViolation entity = toEntity(dto);
        entity.setId(id);
        violationMapper.updateById(entity);
        addLog(dto.getShopId(), "修改违规", "违规ID：" + id, "system");
    }

    /** 删除违规记录 */
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long id) {
        ShopViolation exist = violationMapper.selectById(id);
        Assert.notNull(exist, "违规记录不存在");
        violationMapper.deleteById(id);
        addLog(exist.getShopId(), "删除违规", "违规ID：" + id, "system");
    }

    /** 详情 */
    public ShopViolation getById(Long id) {
        ShopViolation vio = violationMapper.selectById(id);
        Assert.notNull(vio, "违规记录不存在");
        return vio;
    }

    /** 分页列表 */
    public PageResult<ShopViolationVO> page(ShopViolationQueryDTO query) {
        PageHelper.startPage(query.getPageNum(), query.getPageSize());
        List<ShopViolationVO> list = violationMapper.selectPage(query);
        return PageResult.of(new PageInfo<>(list));
    }

    /** 导出数据 */
    public List<ShopViolationVO> listForExport(ShopViolationQueryDTO query) {
        return violationMapper.selectForExport(query);
    }

    // -------- private --------

    private ShopViolation toEntity(ShopViolationDTO dto) {
        ShopViolation entity = new ShopViolation();
        entity.setShopId(dto.getShopId());
        entity.setVioType(dto.getVioType());
        entity.setVioContent(dto.getVioContent());
        entity.setVioTime(dto.getVioTime());
        entity.setDeductionScore(dto.getDeductionScore());
        entity.setHandleResult(dto.getHandleResult());
        return entity;
    }

    private void addLog(Long shopId, String type, String content, String user) {
        ShopOperateLog log = new ShopOperateLog();
        log.setShopId(shopId);
        log.setOperateType(type);
        log.setOperateContent(content);
        log.setOperateUser(user);
        logMapper.insert(log);
    }
}
