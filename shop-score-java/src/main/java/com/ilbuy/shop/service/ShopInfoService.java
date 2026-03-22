package com.ilbuy.shop.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.ilbuy.shop.common.PageResult;
import com.ilbuy.shop.dto.ShopInfoDTO;
import com.ilbuy.shop.dto.ShopInfoQueryDTO;
import com.ilbuy.shop.entity.ShopInfo;
import com.ilbuy.shop.mapper.ShopInfoMapper;
import com.ilbuy.shop.mapper.ShopLogMapper;
import com.ilbuy.shop.vo.ShopInfoVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.Assert;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ShopInfoService {

    private final ShopInfoMapper shopInfoMapper;
    private final ShopLogMapper  logMapper;

    /** 新增商铺 */
    @Transactional(rollbackFor = Exception.class)
    public Long add(ShopInfoDTO dto) {
        ShopInfo entity = toEntity(dto);
        entity.setShopStatus(1); // 默认正常
        shopInfoMapper.insert(entity);
        addLog(entity.getShopId(), "新增商铺", "商铺名称：" + entity.getShopName(), "system");
        return entity.getShopId();
    }

    /** 修改商铺 */
    @Transactional(rollbackFor = Exception.class)
    public void update(ShopInfoDTO dto) {
        Assert.notNull(dto.getShopId(), "商铺ID不能为空");
        ShopInfo entity = toEntity(dto);
        shopInfoMapper.updateById(entity);
        addLog(dto.getShopId(), "修改商铺", "商铺ID：" + dto.getShopId(), "system");
    }

    /** 删除商铺（逻辑删除） */
    @Transactional(rollbackFor = Exception.class)
    public void delete(Long shopId) {
        shopInfoMapper.deleteById(shopId);
        addLog(shopId, "删除商铺", "商铺ID：" + shopId, "system");
    }

    /** 详情 */
    public ShopInfo getById(Long shopId) {
        ShopInfo info = shopInfoMapper.selectById(shopId);
        Assert.notNull(info, "商铺不存在");
        return info;
    }

    /** 分页列表 */
    public PageResult<ShopInfoVO> page(ShopInfoQueryDTO query) {
        PageHelper.startPage(query.getPageNum(), query.getPageSize());
        List<ShopInfoVO> list = shopInfoMapper.selectPage(query);
        return PageResult.of(new PageInfo<>(list));
    }

    /** 导出数据（不分页） */
    public List<ShopInfoVO> listForExport(ShopInfoQueryDTO query) {
        return shopInfoMapper.selectForExport(query);
    }

    // -------- private --------

    private ShopInfo toEntity(ShopInfoDTO dto) {
        ShopInfo entity = new ShopInfo();
        entity.setShopId(dto.getShopId());
        entity.setShopName(dto.getShopName());
        entity.setCateId(dto.getCateId());
        entity.setContactUser(dto.getContactUser());
        entity.setContactPhone(dto.getContactPhone());
        entity.setShopStatus(dto.getShopStatus());
        entity.setJoinTime(dto.getJoinTime());
        entity.setRemark(dto.getRemark());
        return entity;
    }

    private void addLog(Long shopId, String type, String content, String user) {
        com.ilbuy.shop.entity.ShopOperateLog log = new com.ilbuy.shop.entity.ShopOperateLog();
        log.setShopId(shopId);
        log.setOperateType(type);
        log.setOperateContent(content);
        log.setOperateUser(user);
        logMapper.insert(log);
    }
}
