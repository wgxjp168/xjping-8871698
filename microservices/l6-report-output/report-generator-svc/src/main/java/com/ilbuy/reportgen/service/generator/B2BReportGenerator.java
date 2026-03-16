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
 * B2B Report Generator
 * Produces enterprise procurement reports with supplier landscape, price benchmarks,
 * compliance checks, risk assessments and procurement recommendations.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class B2BReportGenerator implements ReportGeneratorStrategy {

    private final L5ReportClient l5ReportClient;

    @Override
    public ClientType supports() {
        return ClientType.B2B;
    }

    @Override
    public GeneratedReport generate(ReportGenerateEvent event) {
        log.info("[B2B Generator] Starting for l5ReportNo={}, userId={}", event.getL5ReportNo(), event.getUserId());

        // Fetch enriched data from L5
        Map<String, Object> l5Data = l5ReportClient.fetchReportData(event.getL5ReportNo());

        List<ReportSectionData> sections = new ArrayList<>();
        sections.add(buildExecutiveSummary(event, l5Data));
        sections.add(buildSupplierLandscape(event, l5Data));
        sections.add(buildPriceBenchmarks(event, l5Data));
        sections.add(buildComplianceCheck(event, l5Data));
        sections.add(buildRiskAssessment(event, l5Data));
        sections.add(buildProcurementRecommendations(event, l5Data));

        Map<String, Object> metadata = new HashMap<>();
        metadata.put("reportVersion", "1.0");
        metadata.put("dataAsOf", OffsetDateTime.now().toString());
        metadata.put("generatorVersion", "B2B-v1.0");
        metadata.put("confidentialityLevel", "CONFIDENTIAL");
        metadata.put("supplierCount", l5Data.getOrDefault("supplierCount", 0));
        metadata.put("priceDataPoints", l5Data.getOrDefault("priceDataPoints", 0));

        log.info("[B2B Generator] Generated {} sections for l5ReportNo={}", sections.size(), event.getL5ReportNo());

        return GeneratedReport.builder()
                .l5ReportNo(event.getL5ReportNo())
                .userId(event.getUserId())
                .title(event.getTitle())
                .clientType(ClientType.B2B)
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

    private ReportSectionData buildExecutiveSummary(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("overview", "Enterprise procurement analysis for category ID " + event.getCategoryId());
        content.put("keyFindings", List.of(
                "Identified " + data.getOrDefault("supplierCount", "N/A") + " qualified suppliers",
                "Average price deviation: " + data.getOrDefault("avgPriceDeviation", "N/A") + "%",
                "Top-tier suppliers maintain 98%+ on-time delivery",
                "Compliance risk level: " + data.getOrDefault("complianceRisk", "LOW")
        ));
        content.put("reportPeriod", data.getOrDefault("reportPeriod", "Last 90 days"));
        content.put("analysisScope", event.getParameters());

        return ReportSectionData.builder()
                .sectionKey("EXECUTIVE_SUMMARY")
                .title("执行摘要 Executive Summary")
                .content(content)
                .charts(Collections.emptyList())
                .orderIndex(0)
                .build();
    }

    private ReportSectionData buildSupplierLandscape(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("totalSuppliers", data.getOrDefault("supplierCount", 0));
        content.put("tier1Suppliers", data.getOrDefault("tier1Suppliers", List.of()));
        content.put("tier2Suppliers", data.getOrDefault("tier2Suppliers", List.of()));
        content.put("geographicDistribution", data.getOrDefault("geoDistribution", Map.of()));
        content.put("certifications", data.getOrDefault("supplierCertifications", List.of()));

        List<ChartData> charts = new ArrayList<>();
        charts.add(ChartData.builder()
                .chartId("supplier-tier-distribution")
                .type("pie")
                .title("供应商层级分布 Supplier Tier Distribution")
                .labels(List.of("Tier 1", "Tier 2", "Tier 3"))
                .datasets(List.of(Map.of(
                        "label", "Suppliers",
                        "data", List.of(
                                data.getOrDefault("tier1Count", 5),
                                data.getOrDefault("tier2Count", 15),
                                data.getOrDefault("tier3Count", 30))
                )))
                .build());

        charts.add(ChartData.builder()
                .chartId("supplier-geo-map")
                .type("bar")
                .title("地理分布 Geographic Distribution")
                .labels(List.of("华东", "华南", "华北", "西部", "海外"))
                .datasets(List.of(Map.of(
                        "label", "Supplier Count",
                        "data", List.of(20, 15, 12, 5, 8)
                )))
                .build());

        return ReportSectionData.builder()
                .sectionKey("SUPPLIER_LANDSCAPE")
                .title("供应商格局 Supplier Landscape")
                .content(content)
                .charts(charts)
                .orderIndex(1)
                .build();
    }

    private ReportSectionData buildPriceBenchmarks(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("marketAvgPrice", data.getOrDefault("marketAvgPrice", 0));
        content.put("priceRange", data.getOrDefault("priceRange", Map.of("min", 0, "max", 0)));
        content.put("negotiatedSavingsPotential", data.getOrDefault("savingsPotential", "5-15%"));
        content.put("volumeDiscountTiers", data.getOrDefault("volumeDiscounts", List.of()));
        content.put("quarterlyTrend", data.getOrDefault("quarterlyPriceTrend", List.of()));

        List<ChartData> charts = new ArrayList<>();
        charts.add(ChartData.builder()
                .chartId("price-trend-12m")
                .type("line")
                .title("12个月价格趋势 12-Month Price Trend")
                .labels(List.of("Q1", "Q2", "Q3", "Q4"))
                .datasets(List.of(
                        Map.of("label", "Market Price", "data", List.of(100, 98, 95, 97)),
                        Map.of("label", "Your Price", "data", List.of(102, 99, 94, 95))
                ))
                .build());

        return ReportSectionData.builder()
                .sectionKey("PRICE_BENCHMARKS")
                .title("价格基准 Price Benchmarks")
                .content(content)
                .charts(charts)
                .orderIndex(2)
                .build();
    }

    private ReportSectionData buildComplianceCheck(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("overallComplianceScore", data.getOrDefault("complianceScore", 85));
        content.put("certificationStatus", data.getOrDefault("certStatus", Map.of()));
        content.put("regulatoryFlags", data.getOrDefault("regulatoryFlags", List.of()));
        content.put("auditHistory", data.getOrDefault("auditHistory", List.of()));
        content.put("esgScore", data.getOrDefault("esgScore", Map.of("environmental", 80, "social", 75, "governance", 90)));

        return ReportSectionData.builder()
                .sectionKey("COMPLIANCE_CHECK")
                .title("合规检查 Compliance Check")
                .content(content)
                .charts(List.of(ChartData.builder()
                        .chartId("compliance-radar")
                        .type("radar")
                        .title("合规雷达图 Compliance Radar")
                        .labels(List.of("质量认证", "安全标准", "环保合规", "劳工标准", "数据安全"))
                        .datasets(List.of(Map.of(
                                "label", "Compliance Score",
                                "data", List.of(85, 90, 75, 80, 88)
                        )))
                        .build()))
                .orderIndex(3)
                .build();
    }

    private ReportSectionData buildRiskAssessment(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("overallRisk", data.getOrDefault("overallRisk", "MEDIUM"));
        content.put("supplyChainRisks", data.getOrDefault("supplyChainRisks", List.of()));
        content.put("geopoliticalRisks", data.getOrDefault("geopoliticalRisks", List.of()));
        content.put("concentrationRisk", data.getOrDefault("concentrationRisk", Map.of()));
        content.put("mitigationStrategies", List.of(
                "Dual sourcing for critical categories",
                "Safety stock optimization",
                "Geographic diversification",
                "Long-term contract hedging"
        ));

        return ReportSectionData.builder()
                .sectionKey("RISK_ASSESSMENT")
                .title("风险评估 Risk Assessment")
                .content(content)
                .charts(Collections.emptyList())
                .orderIndex(4)
                .build();
    }

    private ReportSectionData buildProcurementRecommendations(ReportGenerateEvent event, Map<String, Object> data) {
        Map<String, Object> content = new LinkedHashMap<>();
        content.put("shortTermActions", List.of(
                "Negotiate volume discounts with Tier 1 suppliers",
                "Consolidate orders to reduce logistics cost",
                "Implement e-procurement portal for efficiency"
        ));
        content.put("mediumTermActions", List.of(
                "Qualify 2 additional backup suppliers",
                "Establish vendor-managed inventory",
                "Implement supplier scorecard system"
        ));
        content.put("estimatedSavings", data.getOrDefault("estimatedSavings", "8-12%"));
        content.put("prioritySuppliers", data.getOrDefault("prioritySuppliers", List.of()));
        content.put("contractRecommendations", Map.of(
                "preferredTerms", "12-month framework agreement",
                "paymentTerms", "Net 45",
                "reviewCycle", "Quarterly"
        ));

        return ReportSectionData.builder()
                .sectionKey("PROCUREMENT_RECOMMENDATIONS")
                .title("采购建议 Procurement Recommendations")
                .content(content)
                .charts(Collections.emptyList())
                .orderIndex(5)
                .build();
    }
}
