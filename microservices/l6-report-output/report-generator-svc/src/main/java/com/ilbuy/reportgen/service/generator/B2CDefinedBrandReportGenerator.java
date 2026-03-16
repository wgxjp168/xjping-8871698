package com.ilbuy.reportgen.service.generator;

import com.ilbuy.reportgen.client.L5ReportClient;
import com.ilbuy.reportgen.model.dto.*;
import com.ilbuy.reportgen.model.enums.ClientType;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.time.OffsetDateTime;
import java.util.*;

/**
 * B2C Defined Brand Report Generator
 * Consumer has already selected a brand – generates deep-dive brand analysis,
 * competitive pricing, channel performance and strategic purchase insights.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class B2CDefinedBrandReportGenerator implements ReportGeneratorStrategy {

    private final L5ReportClient l5ReportClient;

    @Override
    public ClientType supports() {
        return ClientType.B2C_DEFINED;
    }

    @Override
    public GeneratedReport generate(ReportGenerateEvent event) {
        log.info("[B2C-Defined Generator] l5ReportNo={}, brandId={}", event.getL5ReportNo(), event.getBrandId());

        Map<String, Object> l5Data = l5ReportClient.fetchReportData(event.getL5ReportNo());

        List<ReportSectionData> sections = new ArrayList<>();
        sections.add(buildBrandAnalysis(event, l5Data));
        sections.add(buildPriceComparison(event, l5Data));
        sections.add(buildCompetitorMapping(event, l5Data));
        sections.add(buildChannelPerformance(event, l5Data));
        sections.add(buildMarketShare(event, l5Data));
        sections.add(buildStrategicInsights(event, l5Data));

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("brandId", event.getBrandId());
        metadata.put("reportVersion", "1.0");
        metadata.put("dataAsOf", OffsetDateTime.now().toString());
        metadata.put("generatorVersion", "B2C-DEFINED-v1.0");

        return GeneratedReport.builder()
                .l5ReportNo(event.getL5ReportNo())
                .userId(event.getUserId())
                .title(event.getTitle())
                .clientType(ClientType.B2C_DEFINED)
                .businessType(event.getBusinessType())
                .brandId(event.getBrandId())
                .categoryId(event.getCategoryId())
                .sections(sections)
                .metadata(metadata)
                .generatedAt(OffsetDateTime.now())
                .generateHtml(event.isGenerateHtml())
                .generatePdf(event.isGeneratePdf())
                .generateExcel(event.isGenerateExcel())
                .deliverEmail(event.isDeliverEmail())
                .emailAddress(event.getEmailAddress())
                .deliverWechat(event.isDeliverWechat())
                .wechatOpenId(event.getWechatOpenId())
                .deliverApp(event.isDeliverApp())
                .appDeviceToken(event.getAppDeviceToken())
                .build();
    }

    private ReportSectionData buildBrandAnalysis(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("brandId", event.getBrandId());
        content.put("brandName", data.getOrDefault("brandName", "Unknown"));
        content.put("brandScore", data.getOrDefault("brandScore", 0));
        content.put("brandTier", data.getOrDefault("brandTier", "STANDARD"));
        content.put("foundedYear", data.getOrDefault("foundedYear", "N/A"));
        content.put("headquartersCountry", data.getOrDefault("hqCountry", "N/A"));
        content.put("productRange", data.getOrDefault("productRange", List.of()));
        content.put("strengths", data.getOrDefault("brandStrengths", List.of()));
        content.put("weaknesses", data.getOrDefault("brandWeaknesses", List.of()));
        content.put("consumerRating", data.getOrDefault("avgConsumerRating", 4.2));
        content.put("reviewCount", data.getOrDefault("reviewCount", 0));

        List<ChartData> charts = List.of(
                ChartData.builder()
                        .chartId("brand-score-trend")
                        .type("line")
                        .title("品牌评分趋势 Brand Score Trend")
                        .labels(List.of("Jan", "Feb", "Mar", "Apr", "May", "Jun"))
                        .datasets(List.of(Map.of(
                                "label", "Brand Score",
                                "data", List.of(78, 80, 79, 82, 85, 84)
                        )))
                        .build()
        );

        return ReportSectionData.builder()
                .sectionKey("BRAND_ANALYSIS")
                .title("品牌分析 Brand Analysis")
                .content(content)
                .charts(charts)
                .orderIndex(0)
                .build();
    }

    private ReportSectionData buildPriceComparison(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("brandAvgPrice", data.getOrDefault("brandAvgPrice", 0));
        content.put("categoryAvgPrice", data.getOrDefault("categoryAvgPrice", 0));
        content.put("premiumVsCategory", data.getOrDefault("premiumPercent", "0%"));
        content.put("priceHistory", data.getOrDefault("priceHistory", List.of()));
        content.put("bestDeals", data.getOrDefault("bestDeals", List.of()));
        content.put("promotionCalendar", data.getOrDefault("promotionCalendar", List.of()));

        List<ChartData> charts = List.of(
                ChartData.builder()
                        .chartId("price-comparison-bar")
                        .type("bar")
                        .title("价格对比 Price Comparison")
                        .labels(List.of("Target Brand", "Category Avg", "Premium Alt", "Budget Alt"))
                        .datasets(List.of(Map.of(
                                "label", "Average Price (CNY)",
                                "data", List.of(
                                        data.getOrDefault("brandAvgPrice", 299),
                                        data.getOrDefault("categoryAvgPrice", 250),
                                        data.getOrDefault("premiumAvgPrice", 450),
                                        data.getOrDefault("budgetAvgPrice", 150)
                                )
                        )))
                        .build()
        );

        return ReportSectionData.builder()
                .sectionKey("PRICE_COMPARISON")
                .title("价格对比 Price Comparison")
                .content(content)
                .charts(charts)
                .orderIndex(1)
                .build();
    }

    private ReportSectionData buildCompetitorMapping(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("directCompetitors", data.getOrDefault("directCompetitors", List.of()));
        content.put("indirectCompetitors", data.getOrDefault("indirectCompetitors", List.of()));
        content.put("competitorPrices", data.getOrDefault("competitorPrices", Map.of()));
        content.put("differentiators", data.getOrDefault("differentiators", List.of()));
        content.put("competitiveAdvantage", data.getOrDefault("competitiveAdvantage", "N/A"));

        return ReportSectionData.builder()
                .sectionKey("COMPETITOR_MAPPING")
                .title("竞争对手映射 Competitor Mapping")
                .content(content)
                .charts(Collections.emptyList())
                .orderIndex(2)
                .build();
    }

    private ReportSectionData buildChannelPerformance(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("channels", data.getOrDefault("salesChannels", List.of()));
        content.put("topChannel", data.getOrDefault("topChannel", "Tmall"));
        content.put("channelPriceDiff", data.getOrDefault("channelPriceDiff", Map.of()));
        content.put("authenticityRisk", data.getOrDefault("authenticityRisk", Map.of()));
        content.put("bestPurchaseChannel", data.getOrDefault("bestPurchaseChannel", "Official Store"));

        List<ChartData> charts = List.of(
                ChartData.builder()
                        .chartId("channel-performance-pie")
                        .type("pie")
                        .title("渠道销售占比 Channel Sales Share")
                        .labels(List.of("天猫", "京东", "拼多多", "官网", "其他"))
                        .datasets(List.of(Map.of(
                                "label", "Sales %",
                                "data", List.of(40, 30, 15, 10, 5)
                        )))
                        .build()
        );

        return ReportSectionData.builder()
                .sectionKey("CHANNEL_PERFORMANCE")
                .title("渠道表现 Channel Performance")
                .content(content)
                .charts(charts)
                .orderIndex(3)
                .build();
    }

    private ReportSectionData buildMarketShare(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("categoryMarketShare", data.getOrDefault("categoryMarketShare", "N/A"));
        content.put("shareGrowthYoY", data.getOrDefault("shareGrowthYoY", "N/A"));
        content.put("marketRank", data.getOrDefault("marketRank", "N/A"));
        content.put("keyMarkets", data.getOrDefault("keyMarkets", List.of()));

        return ReportSectionData.builder()
                .sectionKey("MARKET_SHARE")
                .title("市场份额 Market Share")
                .content(content)
                .charts(Collections.emptyList())
                .orderIndex(4)
                .build();
    }

    private ReportSectionData buildStrategicInsights(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("purchaseRecommendation", data.getOrDefault("purchaseRecommendation", "BUY"));
        content.put("optimalPurchaseTiming", data.getOrDefault("optimalTiming", "Double 11, 618"));
        content.put("valueScore", data.getOrDefault("valueScore", 82));
        content.put("alternativeRecommendations", data.getOrDefault("alternatives", List.of()));
        content.put("watchlistAlerts", data.getOrDefault("watchlistAlerts", List.of()));
        content.put("priceDropPrediction", data.getOrDefault("priceDropPrediction", Map.of(
                "probability", "35%",
                "expectedDrop", "8-15%",
                "timeframe", "Next 30 days"
        )));

        return ReportSectionData.builder()
                .sectionKey("STRATEGIC_INSIGHTS")
                .title("战略洞察 Strategic Insights")
                .content(content)
                .charts(Collections.emptyList())
                .orderIndex(5)
                .build();
    }
}
