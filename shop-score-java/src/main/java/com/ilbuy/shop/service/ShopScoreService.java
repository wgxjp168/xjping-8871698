package com.ilbuy.shop.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.ilbuy.shop.common.PageResult;
import com.ilbuy.shop.constant.ShopScoreConstants;
import com.ilbuy.shop.dto.ShopScoreDTO;
import com.ilbuy.shop.dto.ShopScoreQueryDTO;
import com.ilbuy.shop.entity.ShopOperateLog;
import com.ilbuy.shop.entity.ShopScoreItem;
import com.ilbuy.shop.entity.ShopScoreMain;
import com.ilbuy.shop.mapper.ShopLogMapper;
import com.ilbuy.shop.mapper.ShopScoreMapper;
import com.ilbuy.shop.vo.ShopScoreDetailVO;
import com.ilbuy.shop.vo.ShopScoreMainVO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.Assert;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ShopScoreService {

    private final ShopScoreMapper scoreMapper;
    private final ShopLogMapper   logMapper;

    /**
     * 保存评分：自动算总分 + 自动评级 + 记日志
     * 同一商铺同一周期已有评分时抛出异常（幂等保护）
     */
    @Transactional(rollbackFor = Exception.class)
    public Long saveScore(ShopScoreDTO dto) {
        // 幂等校验
        ShopScoreMain exist = scoreMapper.selectByShopAndPeriod(dto.getShopId(), dto.getScorePeriod());
        Assert.isNull(exist, "该商铺在周期 [" + dto.getScorePeriod() + "] 已存在评分记录，请勿重复提交");

        // 校验各项分值不超满分
        for (ShopScoreDTO.ScoreItemDTO item : dto.getItemList()) {
            BigDecimal fullScore = ShopScoreConstants.FULL_SCORE_MAP.get(item.getScoreRule());
            Assert.notNull(fullScore, "未知评分规则：" + item.getScoreRule());
            Assert.isTrue(
                item.getActualScore().compareTo(fullScore) <= 0,
                ShopScoreConstants.SCORE_RULE_NAME_MAP.get(item.getScoreRule())
                    + " 实际分值不能超过满分 " + fullScore
            );
        }

        // 计算总分
        BigDecimal total = dto.getItemList().stream()
            .map(ShopScoreDTO.ScoreItemDTO::getActualScore)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        // 评级
        String level = calcLevel(total);

        // 保存主表
        ShopScoreMain main = new ShopScoreMain();
        main.setShopId(dto.getShopId());
        main.setScorePeriod(dto.getScorePeriod());
        main.setTotalScore(total);
        main.setShopLevel(level);
        main.setScoreUser(dto.getScoreUser());
        main.setScoreTime(LocalDateTime.now());
        main.setOpinion(dto.getOpinion());
        scoreMapper.insertMain(main);

        // 保存明细（带满分）
        List<ShopScoreItem> items = dto.getItemList().stream().map(i -> {
            ShopScoreItem item = new ShopScoreItem();
            item.setMainId(main.getMainId());
            item.setShopId(dto.getShopId());
            item.setScoreRule(i.getScoreRule());
            item.setFullScore(ShopScoreConstants.FULL_SCORE_MAP.get(i.getScoreRule()));
            item.setActualScore(i.getActualScore());
            item.setRemark(i.getRemark());
            return item;
        }).collect(Collectors.toList());
        scoreMapper.batchInsertItem(items);

        // 记操作日志
        addLog(dto.getShopId(), "商铺评分",
            "周期：" + dto.getScorePeriod() + "  总分：" + total + "  等级：" + level,
            dto.getScoreUser());

        return main.getMainId();
    }

    /**
     * 评分详情（含明细列表）
     */
    public ShopScoreDetailVO getDetail(Long mainId) {
        ShopScoreMain main = scoreMapper.selectMainById(mainId);
        Assert.notNull(main, "评分记录不存在");

        List<ShopScoreDetailVO.ItemVO> items = scoreMapper.selectItemsByMainId(mainId);

        ShopScoreDetailVO vo = new ShopScoreDetailVO();
        vo.setMainId(main.getMainId());
        vo.setShopId(main.getShopId());
        vo.setScorePeriod(main.getScorePeriod());
        vo.setTotalScore(main.getTotalScore());
        vo.setShopLevel(main.getShopLevel());
        vo.setScoreUser(main.getScoreUser());
        vo.setScoreTime(main.getScoreTime());
        vo.setOpinion(main.getOpinion());
        vo.setItemList(items);
        return vo;
    }

    /**
     * 分页列表
     */
    public PageResult<ShopScoreMainVO> page(ShopScoreQueryDTO query) {
        PageHelper.startPage(query.getPageNum(), query.getPageSize());
        List<ShopScoreMainVO> list = scoreMapper.selectPage(query);
        return PageResult.of(new PageInfo<>(list));
    }

    /**
     * 导出数据（不分页）
     */
    public List<ShopScoreMainVO> listForExport(ShopScoreQueryDTO query) {
        return scoreMapper.selectForExport(query);
    }

    // -------- private --------

    /** 等级计算：A≥90 B≥80 C≥70 D<70 */
    private String calcLevel(BigDecimal total) {
        int t = total.intValue();
        if (t >= ShopScoreConstants.LEVEL_A_MIN) return "A";
        if (t >= ShopScoreConstants.LEVEL_B_MIN) return "B";
        if (t >= ShopScoreConstants.LEVEL_C_MIN) return "C";
        return "D";
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
