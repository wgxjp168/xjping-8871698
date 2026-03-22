package com.ilbuy.supplier.service;

import com.github.pagehelper.PageHelper;
import com.github.pagehelper.PageInfo;
import com.ilbuy.supplier.common.PageResult;
import com.ilbuy.supplier.constant.SupplierScoreConstant;
import com.ilbuy.supplier.dto.SupplierScoreDTO;
import com.ilbuy.supplier.dto.SupplierScoreQueryDTO;
import com.ilbuy.supplier.entity.SupplierLog;
import com.ilbuy.supplier.entity.SupplierScoreItem;
import com.ilbuy.supplier.entity.SupplierScoreMain;
import com.ilbuy.supplier.mapper.SupplierLogMapper;
import com.ilbuy.supplier.mapper.SupplierScoreMapper;
import com.ilbuy.supplier.vo.SupplierScoreDetailVO;
import com.ilbuy.supplier.vo.SupplierScoreMainVO;
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
public class SupplierScoreService {

    private final SupplierScoreMapper scoreMapper;
    private final SupplierLogMapper   logMapper;

    /**
     * 保存评分：自动算总分 + 自动评级 + 记日志
     * 同一供应商同一周期已有评分时抛出异常（幂等保护）
     */
    @Transactional(rollbackFor = Exception.class)
    public Long saveScore(SupplierScoreDTO dto) {
        // 幂等校验
        SupplierScoreMain exist = scoreMapper.selectBySupplierAndPeriod(
            dto.getSupplierId(), dto.getScorePeriod());
        Assert.isNull(exist,
            "该供应商在周期 [" + dto.getScorePeriod() + "] 已存在评分记录，请勿重复提交");

        // 校验各项分值不超满分
        for (SupplierScoreDTO.ItemDTO item : dto.getItemList()) {
            BigDecimal fullScore = SupplierScoreConstant.FULL_SCORE.get(item.getScoreType());
            Assert.notNull(fullScore, "未知评分类型：" + item.getScoreType());
            Assert.isTrue(
                item.getActualScore().compareTo(fullScore) <= 0,
                SupplierScoreConstant.TYPE_NAME_MAP.get(item.getScoreType())
                    + " 实际分值不能超过满分 " + fullScore
            );
        }

        // 计算总分
        BigDecimal total = dto.getItemList().stream()
            .map(SupplierScoreDTO.ItemDTO::getActualScore)
            .reduce(BigDecimal.ZERO, BigDecimal::add);

        // 评级
        String level = SupplierScoreConstant.getLevel(total);

        // 保存主表
        SupplierScoreMain main = new SupplierScoreMain();
        main.setSupplierId(dto.getSupplierId());
        main.setScorePeriod(dto.getScorePeriod());
        main.setTotalScore(total);
        main.setSupplierLevel(level);
        main.setScoreUser(dto.getScoreUser());
        main.setScoreTime(LocalDateTime.now());
        main.setOpinion(dto.getOpinion());
        scoreMapper.insertMain(main);

        // 保存明细（带满分）
        List<SupplierScoreItem> items = dto.getItemList().stream().map(i -> {
            SupplierScoreItem item = new SupplierScoreItem();
            item.setMainId(main.getMainId());
            item.setSupplierId(dto.getSupplierId());
            item.setScoreType(i.getScoreType());
            item.setFullScore(SupplierScoreConstant.FULL_SCORE.get(i.getScoreType()));
            item.setActualScore(i.getActualScore());
            item.setRemark(i.getRemark());
            return item;
        }).collect(Collectors.toList());
        scoreMapper.batchInsertItem(items);

        // 记操作日志
        addLog(dto.getSupplierId(), "供应商评分",
            "周期：" + dto.getScorePeriod() + "  总分：" + total + "  等级：" + level,
            dto.getScoreUser());

        return main.getMainId();
    }

    /**
     * 评分详情（含明细列表）
     */
    public SupplierScoreDetailVO getDetail(Long mainId) {
        SupplierScoreMain main = scoreMapper.selectMainById(mainId);
        Assert.notNull(main, "评分记录不存在");

        List<SupplierScoreDetailVO.ItemVO> items = scoreMapper.selectItemsByMainId(mainId);

        SupplierScoreDetailVO vo = new SupplierScoreDetailVO();
        vo.setMainId(main.getMainId());
        vo.setSupplierId(main.getSupplierId());
        vo.setScorePeriod(main.getScorePeriod());
        vo.setTotalScore(main.getTotalScore());
        vo.setSupplierLevel(main.getSupplierLevel());
        vo.setScoreUser(main.getScoreUser());
        vo.setScoreTime(main.getScoreTime());
        vo.setOpinion(main.getOpinion());
        vo.setItemList(items);
        return vo;
    }

    /**
     * 分页列表
     */
    public PageResult<SupplierScoreMainVO> page(SupplierScoreQueryDTO query) {
        PageHelper.startPage(query.getPageNum(), query.getPageSize());
        List<SupplierScoreMainVO> list = scoreMapper.selectPage(query);
        return PageResult.of(new PageInfo<>(list));
    }

    /**
     * 导出数据（不分页）
     */
    public List<SupplierScoreMainVO> listForExport(SupplierScoreQueryDTO query) {
        return scoreMapper.selectForExport(query);
    }

    // -------- private --------

    private void addLog(Long supplierId, String type, String content, String user) {
        SupplierLog log = new SupplierLog();
        log.setSupplierId(supplierId);
        log.setOperateType(type);
        log.setOperateContent(content);
        log.setOperateUser(user);
        logMapper.insert(log);
    }
}
