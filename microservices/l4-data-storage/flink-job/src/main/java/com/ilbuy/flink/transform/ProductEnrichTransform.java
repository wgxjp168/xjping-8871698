package com.ilbuy.flink.transform;

import com.ilbuy.flink.model.ProductEvent;
import org.apache.flink.api.common.functions.RichMapFunction;
import org.apache.flink.configuration.Configuration;

/**
 * Flink 富化转换算子
 *
 * 职责：
 * 1. 计算评分分位数标签（TOP10 / TOP25 / REST）
 * 2. 过滤 mock 数据（is_mock=true 不写入分析表）
 * 3. 标准化空值
 */
public class ProductEnrichTransform extends RichMapFunction<ProductEvent, ProductEvent> {

    private static final long serialVersionUID = 1L;

    // 分位数阈值（基于历史数据校准，可通过广播状态动态更新）
    private static final double TOP10_THRESHOLD = 85.0;
    private static final double TOP25_THRESHOLD = 70.0;

    @Override
    public void open(Configuration parameters) {
        // 可在此初始化广播状态、连接外部配置中心等
    }

    @Override
    public ProductEvent map(ProductEvent event) {
        // 过滤 mock 数据
        if (Boolean.TRUE.equals(event.getIsMock())) {
            return null;   // Flink 的 flatMap 或 filter 更合适，此处简化处理
        }

        // 评分分位数标签
        double score = event.getTotalScore() != null ? event.getTotalScore() : 0.0;
        if (score >= TOP10_THRESHOLD) {
            event.setScorePercentile("TOP10");
        } else if (score >= TOP25_THRESHOLD) {
            event.setScorePercentile("TOP25");
        } else {
            event.setScorePercentile("REST");
        }

        // 空值标准化
        if (event.getSalesCount() == null)   event.setSalesCount(0);
        if (event.getReviewCount() == null)  event.setReviewCount(0);
        if (event.getAverageRating() == null) event.setAverageRating(0.0);

        return event;
    }
}
