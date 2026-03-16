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
 * B2C Undefined Brand Report Generator
 * Consumer hasn't selected a brand – generates market overview, category trends,
 * brand discovery, price range analysis, consumer sentiment, and entry strategy.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class B2CUndefinedBrandReportGenerator implements ReportGeneratorStrategy {

    private final L5ReportClient l5ReportClient;

    @Override
    public ClientType supports() {
        return ClientType.B2C_UNDEFINED;
    }

    @Override
    public GeneratedReport generate(ReportGenerateEvent event) {
        log.info("[B2C-Undefined Generator] l5ReportNo={}, categoryId={}", event.getL5ReportNo(), event.getCategoryId());

        Map<String, Object> l5Data = l5ReportClient.fetchReportData(event.getL5ReportNo());

        List<ReportSectionData> sections = new ArrayList<>();
        sections.add(buildMarketOverview(event, l5Data));
        sections.add(buildCategoryTrends(event, l5Data));
        sections.add(buildBrandDiscovery(event, l5Data));
        sections.add(buildPriceRangeAnalysis(event, l5Data));
        sections.add(buildConsumerSentiment(event, l5Data));
        sections.add(buildEntryStrategy(event, l5Data));

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("categoryId", event.getCategoryId());
        metadata.put("reportVersion", "1.0");
        metadata.put("dataAsOf", OffsetDateTime.now().toString());
        metadata.put("generatorVersion", "B2C-UNDEFINED-v1.0");

        return GeneratedReport.builder()
                .l5ReportNo(event.getL5ReportNo())
                .userId(event.getUserId())
                .title(event.getTitle())
                .clientType(ClientType.B2C_UNDEFINED)
                .businessType(event.getBusinessType())
                .brandId(null)
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

    private ReportSectionData buildMarketOverview(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("categoryName", data.getOrDefault("categoryName", "Unknown Category"));
        content.put("marketSize", data.getOrDefault("marketSize", "N/A"));
        content.put("marketGrowthRate", data.getOrDefault("marketGrowthRate", "N/A"));
        content.put("totalActiveBrands", data.getOrDefault("activeBrandCount", 0));
        content.put("totalActiveProducts", data.getOrDefault("activeProductCount", 0));
        content.put("keyDrivers", data.getOrDefault("marketDrivers", List.of(
                "Rising disposable income",
                "E-commerce penetration",
                "Consumer preference shift"
        )));

        List<ChartData> charts = List.of(
                ChartData.builder()
                        .chartId("market-size-trend")
                        .type("bar")
                        .title("市场规模趋势 Market Size Trend (亿元 CNY)")
                        .labels(List.of("2021", "2022", "2023", "2024", "2025E"))
                        .datasets(List.of(Map.of(
                                "label", "Market Size (亿元)",
                                "data", List.of(320, 380, 450, 520, 610)
                        )))
                        .build()
        );

        return ReportSectionData.builder()
                .sectionKey("MARKET_OVERVIEW")
                .title("市场总览 Market Overview")
                .content(content)
                .charts(charts)
                .orderIndex(0)
                .build();
    }

    private ReportSectionData buildCategoryTrends(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("hotSubcategories", data.getOrDefault("hotSubcategories", List.of()));
        content.put("emergingTrends", data.getOrDefault("emergingTrends", List.of(
                "Sustainability focus",
                "Premiumization trend",
                "Health & wellness integration"
        )));
        content.put("decliningSubcategories", data.getOrDefault("decliningSubcategories", List.of()));
        content.put("seasonalPatterns", data.getOrDefault("seasonalPatterns", Map.of()));
        content.put("searchVolumeGrowth", data.getOrDefault("searchVolumeGrowth", "N/A"));

        List<ChartData> charts = List.of(
                ChartData.builder()
                        .chartId("search-trend-line")
                        .type("line")
                        .title("搜索热度趋势 Search Volume Trend")
                        .labels(List.of("Q1'24", "Q2'24", "Q3'24", "Q4'24", "Q1'25"))
                        .datasets(List.of(
                                Map.of("label", "Category Search", "data", List.of(100, 115, 130, 160, 145)),
                                Map.of("label", "Top Keyword", "data", List.of(80, 95, 110, 140, 125))
                        ))
                        .build()
        );

        return ReportSectionData.builder()
                .sectionKey("CATEGORY_TRENDS")
                .title("品类趋势 Category Trends")
                .content(content)
                .charts(charts)
                .orderIndex(1)
                .build();
    }

    private ReportSectionData buildBrandDiscovery(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("topBrands", data.getOrDefault("topBrands", List.of()));
        content.put("risingBrands", data.getOrDefault("risingBrands", List.of()));
        content.put("premiumBrands", data.getOrDefault("premiumBrands", List.of()));
        content.put("valueBrands", data.getOrDefault("valueBrands", List.of()));
        content.put("nischBrands", data.getOrDefault("nicheBrands", List.of()));
        content.put("brandRecommendations", buildBrandRecommendations(data));

        List<ChartData> charts = List.of(
                ChartData.builder()
                        .chartId("brand-market-share-pie")
                        .type("pie")
                        .title("品牌市场份额 Brand Market Share")
                        .labels(List.of("Brand A", "Brand B", "Brand C", "Brand D", "Others"))
                        .datasets(List.of(Map.of(
                                "label", "Market Share %",
                                "data", List.of(28, 22, 18, 12, 20)
                        )))
                        .build()
        );

        return ReportSectionData.builder()
                .sectionKey("BRAND_DISCOVERY")
                .title("品牌发现 Brand Discovery")
                .content(content)
                .charts(charts)
                .orderIndex(2)
                .build();
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> buildBrandRecommendations(Map<String, Object> data) {
        List<Map<String, Object>> recs = new ArrayList<>();
        recs.add(Map.of(
                "rank", 1,
                "brandId", data.getOrDefault("topBrandId", 1001),
                "brandName", data.getOrDefault("topBrandName", "Brand A"),
                "reason", "Market leader with best value-for-money",
                "matchScore", 92,
                "avgPrice", data.getOrDefault("topBrandPrice", 299)
        ));
        recs.add(Map.of(
                "rank", 2,
                "brandId", data.getOrDefault("risingBrandId", 1002),
                "brandName", data.getOrDefault("risingBrandName", "Brand B"),
                "reason", "Rising brand with strong consumer sentiment",
                "matchScore", 87,
                "avgPrice", data.getOrDefault("risingBrandPrice", 259)
        ));
        return recs;
    }

    private ReportSectionData buildPriceRangeAnalysis(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("budgetTier", Map.of("range", "< 100元", "brands", data.getOrDefault("budgetBrands", List.of())));
        content.put("midTier", Map.of("range", "100-500元", "brands", data.getOrDefault("midBrands", List.of())));
        content.put("premiumTier", Map.of("range", "500-2000元", "brands", data.getOrDefault("premiumBrands2", List.of())));
        content.put("luxuryTier", Map.of("range", "> 2000元", "brands", data.getOrDefault("luxuryBrands", List.of())));
        content.put("sweetSpot", data.getOrDefault("sweetSpotRange", "200-400元"));
        content.put("volumeByTier", data.getOrDefault("volumeByTier", Map.of()));

        return ReportSectionData.builder()
                .sectionKey("PRICE_RANGE_ANALYSIS")
                .title("价格区间分析 Price Range Analysis")
                .content(content)
                .charts(List.of(ChartData.builder()
                        .chartId("price-tier-volume")
                        .type("bar")
                        .title("各价格段销量分布")
                        .labels(List.of("<100元", "100-500元", "500-2000元", ">2000元"))
                        .datasets(List.of(Map.of(
                                "label", "Sales Volume %",
                                "data", List.of(15, 55, 25, 5)
                        )))
                        .build()))
                .orderIndex(3)
                .build();
    }

    private ReportSectionData buildConsumerSentiment(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("overallSentiment", data.getOrDefault("overallSentiment", "POSITIVE"));
        content.put("sentimentScore", data.getOrDefault("sentimentScore", 72));
        content.put("topPositiveKeywords", data.getOrDefault("positiveKeywords", List.of("性价比高", "质量好", "快递快")));
        content.put("topNegativeKeywords", data.getOrDefault("negativeKeywords", List.of("售后差", "包装简陋")));
        content.put("consumerProfileInsights", data.getOrDefault("consumerProfiles", Map.of(
                "ageGroup", "25-35岁",
                "genderSplit", "Female 60% / Male 40%",
                "topCities", List.of("北京", "上海", "广州", "成都")
        )));

        return ReportSectionData.builder()
                .sectionKey("CONSUMER_SENTIMENT")
                .title("消费者情感分析 Consumer Sentiment")
                .content(content)
                .charts(Collections.emptyList())
                .orderIndex(4)
                .build();
    }

    private ReportSectionData buildEntryStrategy(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("purchaseGuidance", "Based on your profile, we recommend starting with mid-tier brands for best value");
        content.put("recommendedBudget", data.getOrDefault("recommendedBudget", "200-400元"));
        content.put("optimalTiming", "Promotional periods: 618 (June), Double 11 (November)");
        content.put("channelAdvice", Map.of(
                "primary", "Tmall Official Stores (天猫旗舰店)",
                "backup", "JD Self-operated (京东自营)",
                "avoid", "Third-party resellers without ratings"
        ));
        content.put("redFlags", List.of(
                "Prices more than 40% below average – likely counterfeit",
                "No authentic product reviews",
                "Sellers with < 100 transactions"
        ));
        content.put("nextSteps", List.of(
                "Shortlist 3 brands from Brand Discovery section",
                "Compare on 我来购ILbuy platform",
                "Set price alert for target product"
        ));

        return ReportSectionData.builder()
                .sectionKey("ENTRY_STRATEGY")
                .title("入场策略 Entry Strategy")
                .content(content)
                .charts(Collections.emptyList())
                .orderIndex(5)
                .build();
    }
}
